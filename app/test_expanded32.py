from sound_catalog30 import stats,match,asset
from sound_effects29 import canonical,planned_effects
from studio_sections import compile_sections
from pathlib import Path
import soundfile as sf
s=stats()
print("TOTAL",s["total_imported_audio"],"CATEGORIES",s["mapped_categories"],"DISTINCT_STEMS",s["searchable_specific_samples"])
cases=[("Heavy metal collision","metal_collision_hifi"),
       ("Glass breaking","glass_break_hifi"),("Metal falling","metal_fall_hifi"),
       ("Dull metal hit","metal_collision_hifi"),("Multiple clicks","clicks_hifi"),
       ("Piano","piano")]
for query,category in cases[:-1]:
 k=canonical(query)
 p=asset(k)
 print(query,k,p.name if p else "MISSING",sf.info(str(p)).samplerate if p else "")
 assert k==category and p and p.is_file()
assert s["total_imported_audio"]>=1600
assert s["mapped_categories"]>=80
print("EXPANDED_CC0_LIBRARY_PASS")
