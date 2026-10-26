#!/usr/bin/env python3
"""Idempotent, backed-up HAPYCH overlays for the pinned external Seed-VC Git tree.

Only .py files present in the source overlay tree may be managed. Upstream
tracked Git files are NEVER overwritten. On upgrades, originals are backed up
before replacing files. If a manifest exists and a user has changed the
previously installed source, the update is refused rather than clobbering it.

Older HAPYCH versions had no manifest; untracked legacy files are backed up
before adopting them. Does not touch voice WAVs, model weights, training runs.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

MANIFEST = ".hapych-overlay-manifest.json"
BACKUPS = ".hapych-overlay-backups"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root: Path, overlay: Path, expected_commit: str) -> dict:
    root = root.resolve(strict=True)
    overlay = overlay.resolve(strict=True)
    if not (root / ".git").exists():
        raise RuntimeError("Expected a Seed-VC Git checkout")
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True)
    if result.returncode or result.stdout.strip() != expected_commit:
        raise RuntimeError("Seed-VC is not at the pinned Git commit. No files changed.")
    if not overlay.is_dir():
        raise RuntimeError("Missing Music Studio voice overlay source directory")

    source_files = {
        path.relative_to(overlay).as_posix(): path
        for path in overlay.rglob("*.py") if path.is_file()
    }
    if not source_files or len(source_files) > 150:
        raise RuntimeError("Missing or unexpected number of Seed-VC overlay files")

    manifest_file = root / MANIFEST
    if manifest_file.is_symlink():
        raise RuntimeError("Overlay manifest is a symlink; refusing")
    old = None
    if manifest_file.is_file():
        old = json.loads(manifest_file.read_text(encoding="utf-8"))
        if old.get("version") != 1 or not isinstance(old.get("files"), dict):
            raise RuntimeError("Invalid HAPYCH overlay manifest, refusing unsafe update")
    previous = old["files"] if old else {}
    legacy = old is None
    actions = []

    # Entire upgrade is preflighted before ANY destination file changes.
    for rel, source in sorted(source_files.items()):
        if not rel.endswith(".py") or rel.startswith("/") or ".." in Path(rel).parts:
            raise RuntimeError("Unsafe overlay filename: " + rel)
        destination = root / rel
        if source.is_symlink() or destination.is_symlink():
            raise RuntimeError("Refusing symlink overlay: " + rel)
        parent = destination.parent
        while parent != root:
            if parent.is_symlink():
                raise RuntimeError("Refusing symlink parent: " + rel)
            parent = parent.parent
        is_upstream = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", rel],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode == 0
        if is_upstream:
            raise RuntimeError("Overlay conflicts with upstream tracked file: " + rel)
        desired_hash = sha(source)
        if destination.exists():
            if not destination.is_file():
                raise RuntimeError("Overlay target is not a regular file: " + rel)
            actual_hash = sha(destination)
            if actual_hash == desired_hash:
                actions.append((rel, source, destination, "skip", desired_hash))
                continue
            if not legacy and (rel not in previous or actual_hash != previous[rel]):
                raise RuntimeError(
                    "An existing overlay has local/user modifications: " + rel +
                    ". No files changed. Back it up and reconcile changes manually."
                )
            actions.append((rel, source, destination,
                            "legacy_upgrade" if legacy else "upgrade", desired_hash))
        else:
            if not legacy and rel in previous:
                raise RuntimeError("Previously installed overlay deleted by user: " + rel)
            actions.append((rel, source, destination, "new", desired_hash))

    # Back up all pre-existing changes first; a failure here changes no source.
    upgrades = [x for x in actions if x[3] in ("legacy_upgrade", "upgrade")]
    backup_root = None
    if upgrades:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_root = root / BACKUPS / (stamp+"-"+uuid.uuid4().hex[:7])
        for rel, _, destination, _, _ in upgrades:
            backup = backup_root / rel
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup)
            if sha(backup) != sha(destination):
                raise RuntimeError("Backup verification failed: " + rel)

    for rel, source, destination, status, checksum in actions:
        if status == "skip":
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(destination.name+".hapych-"+uuid.uuid4().hex[:8]+".tmp")
        try:
            shutil.copyfile(source, temp)
            if sha(temp) != checksum:
                raise RuntimeError("Overlay temporary copy is corrupt: " + rel)
            os.replace(temp, destination)
            if sha(destination) != checksum:
                raise RuntimeError("Overlay target checksum mismatch: " + rel)
        finally:
            if temp.exists():
                temp.unlink()

    manifest = {
        "version": 1,
        "upstream_commit": expected_commit,
        "files": {rel: digest for rel, _, _, _, digest in actions}
    }
    temp_manifest = manifest_file.with_name(MANIFEST+".tmp-"+uuid.uuid4().hex[:8])
    try:
        temp_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n",
                                 encoding="utf-8")
        os.replace(temp_manifest, manifest_file)
    finally:
        if temp_manifest.exists():
            temp_manifest.unlink()

    status = {key: sum(x[3] == key for x in actions)
              for key in ("new", "skip", "legacy_upgrade", "upgrade")}
    print("SEED_OVERLAYS_OK", json.dumps(status, ensure_ascii=False),
          "backup="+(str(backup_root) if backup_root else "none"), flush=True)
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-root", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--expected-commit", type=str, required=True)
    args = parser.parse_args()
    try:
        run(args.seed_root, args.overlay, args.expected_commit)
        return 0
    except Exception as exc:
        print("SEED_OVERLAY_FAILED: "+str(exc), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
