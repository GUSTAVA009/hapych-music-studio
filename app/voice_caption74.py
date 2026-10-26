"""QA74: preserve reference-supported baritone register instruction in ACE caption.

The user-supplied 512-char musical prompt is authoritative. This module does not
rewrite song lyrics, transpose the audio or claim to clone a voice. It edits only
existing *baritone* descriptors when a reliable low reference pitch is available.
"""
from __future__ import annotations
import re

MAX_CAPTION = 512
_COMPACT = (
    ("cinematic development and strong musical climax", "cinematic build and climax"),
    ("dark 2000s urban crime noir", "dark 2000s urban noir"),
    ("punchy kick, snare and hi-hats", "punchy kick/snare/hi-hats"),
    ("native Russian diction, sustained legato", "native Russian diction, legato"),
    ("wide spacious stereo mix, defined depth", "wide stereo depth"),
    ("emotional melancholy, tension", "melancholy and tension"),
)

def integrate(caption: str, profile: dict, max_chars: int = MAX_CAPTION) -> dict:
    """Return caption plus explicit decision; do not silently drop voice hint."""
    original = str(caption)
    report = {
        "caption": original,
        "status": "not_applicable",
        "changed": False,
        "reference_hz": None,
        "reference_hint_sent_to_model": False,
        "reason": "",
        "compactions": [],
    }
    if not profile or not profile.get("reliable"):
        report["reason"] = "No reliable voice-reference pitch profile"
        return report
    try:
        median = float(profile["median_hz"])
        upper = float(profile["p85_hz"])
    except (TypeError, ValueError, KeyError):
        report["reason"] = "Incomplete voice pitch profile"
        return report
    report["reference_hz"] = {"median": median, "p85": upper}
    if not (70 <= median < 165 and 80 <= upper < 195):
        report["reason"] = "Reference does not clearly call for low-register guidance"
        return report
    # Never override an explicitly requested tenor or high lead.
    if re.search(r"\btenor\b|\bfalsetto\b|\bhigh[- ]register\b", original, re.I):
        report["status"] = "explicit_user_style_preserved"
        report["reason"] = "An explicit high-register instruction takes precedence"
        return report
    if re.search(r"\blow\b.{0,20}\bbaritone\b|\bdeep\b.{0,20}\bbaritone\b", original, re.I):
        report.update(status="already_included", reference_hint_sent_to_model=True,
                      reason="Low baritone guidance already in caption")
        return report
    # Insert the smallest possible change; existing connected/legato instructions
    # are retained exactly. No arbitrary numeric F0 restriction on singing.
    changed, count = re.subn(r"\bmale baritone\b", "low male baritone", original,
                             count=1, flags=re.I)
    if not count:
        changed, count = re.subn(r"\bbaritone\b", "low baritone", original,
                                 count=1, flags=re.I)
    if not count:
        report["reason"] = "No baritone direction to amend without inventing style"
        return report
    compacted = []
    if len(changed) > max_chars:
        for before, after in _COMPACT:
            if before in changed:
                changed = changed.replace(before, after, 1)
                compacted.append(before + " -> " + after)
                if len(changed) <= max_chars:
                    break
    if len(changed) > max_chars:
        # Whitespace compaction does not discard a single requirement.
        changed = changed.replace("; ", ";")
        compacted.append("removed optional spaces after semicolons")
    if len(changed) > max_chars:
        report.update(status="not_fitted", reason="Could not fit register hint while preserving musical requirements",
                      compactions=compacted)
        return report
    report.update(caption=changed, status="integrated", changed=True,
                  reference_hint_sent_to_model=True,
                  reason="Reliable low F0 was merged with the existing baritone requirement",
                  compactions=compacted)
    return report
