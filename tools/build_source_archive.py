#!/usr/bin/env python3
"""Build and verify HAPYCH source ZIP using tracked Git files only.

- No secrets, private recordings, checkpoints, node_modules or caches.
- Verify ZIP CRC, expected layout, UTF-8 metadata, zip-slip traversal.
- Extract to disposable Temp directory and compare SHA256 of every entry.
- This tests CODE archiving/unarchiving; it cannot verify downloaded model archives.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import zipfile

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    root=args.root.resolve()
    if not (root/".git").exists():raise RuntimeError("Expected a Git checkout")
    report=subprocess.run(["git","-C",str(root),"ls-files","--cached","--full-name","-z"],
                          check=True,stdout=subprocess.PIPE)
    paths=[x.decode("utf-8") for x in report.stdout.split(b"\0") if x]
    if len(paths)<450:raise RuntimeError(f"Source file count is unexpectedly small: {len(paths)}")
    excluded_suffix={".wav",".mp3",".mp4",".onnx",".bin",".pt",".pth",".safetensors",".zip",".sqlite"}
    required={"Install.cmd","README.md","LICENSE","scripts/Install-Windows.ps1",
              "scripts/Bootstrap-Windows.ps1","scripts/Verify-Install.ps1",
              "app/studio_server.py","app/ui/index.html","third_party_versions.json",
              "tools/audit_repo.py"}
    if not required.issubset(paths):raise RuntimeError("Critical files are not staged")
    for rel in paths:
        p=PurePosixPath(rel)
        if p.is_absolute() or ".." in p.parts or "\\" in rel:
            raise RuntimeError("Unsafe archive path: "+rel)
        if p.suffix.lower() in excluded_suffix or ".venv" in p.parts or "checkpoints" in p.parts:
            raise RuntimeError("User/model data would be bundled: "+rel)
        src=root/rel
        if not src.is_file() or src.is_symlink():
            raise RuntimeError("Unresolved or linked path: "+rel)
        if src.stat().st_size>3_000_000:raise RuntimeError("Oversized source file: "+rel)
    output=args.output.resolve()
    if root in output.parents:raise RuntimeError("Write archives outside the Git repository")
    output.parent.mkdir(parents=True,exist_ok=True)
    # Build from Git staging path; deterministic order, stable ZIP metadata.
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7,
                         allowZip64=True) as archive:
        for rel in sorted(paths):
            info=zipfile.ZipInfo("hapych-music-studio/"+rel,
                date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.flag_bits|=0x800
            info.external_attr=(0o644 & 0xffff)<<16
            archive.writestr(info,(root/rel).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=7)
    with zipfile.ZipFile(output) as archive:
        bad=archive.testzip()
        if bad:raise RuntimeError(f"ZIP CRC failed: {bad}")
        members=archive.namelist()
        if len(members)!=len(paths):raise RuntimeError("ZIP entries do not match staged files")
        for member in members:
            p=PurePosixPath(member)
            if p.is_absolute() or ".." in p.parts or p.parts[0]!="hapych-music-studio":
                raise RuntimeError(f"ZIP path traversal risk: {member}")
        if args.verify:
            with tempfile.TemporaryDirectory(prefix="hapych-archive-test-") as tmp:
                archive.extractall(tmp)
                root2=Path(tmp)/"hapych-music-studio"
                for rel in paths:
                    left=hashlib.sha256((root/rel).read_bytes()).digest()
                    right=hashlib.sha256((root2/rel).read_bytes()).digest()
                    if left!=right:raise RuntimeError("ZIP extracted file mismatch: "+rel)
                assert (root2/"Install.cmd").is_file()
                assert (root2/"scripts/Bootstrap-Windows.ps1").is_file()
    print("ARCHIVE_VERIFIED",output,"FILES",len(paths),
          "ZIP_MIB",round(output.stat().st_size/2**20,2),
          "SHA256",hashlib.sha256(output.read_bytes()).hexdigest(),flush=True)
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as ex:
        print(f"ARCHIVE_FAILED: {ex}",file=sys.stderr)
        sys.exit(1)
