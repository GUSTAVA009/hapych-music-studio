from sound_catalog30 import stats,match,asset
from sound_effects29 import canonical,_asset_path
s=stats();cats=s["categories"];checked=0;bad=[]
for c in cats:
 key=c["id"]
 got=canonical(key)
 f=_asset_path(got) if got else None
 if got!=key or not f or not f.is_file():bad.append((key,got))
 else:checked+=1
for k in ("human_laughter","metal_collision_hifi","night_ambience","phone_ring","glass_break_hifi"):
 assert canonical(k)==k,k
assert checked==len(cats),(checked,len(cats),bad)
samples=s["total_imported_audio"]
print("SFX_ROUNDTRIP_PASS",checked,"CATEGORIES",samples,"FILES")
