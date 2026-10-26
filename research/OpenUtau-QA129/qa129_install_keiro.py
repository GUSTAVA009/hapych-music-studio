"""Install verified official LUNAI voicebank into isolated OpenUtau portable directory.
No user voice data or production Music Studio touched.
Only create metadata character.txt if upstream ships an empty placeholder.
"""
import zipfile, pathlib, hashlib, json, sys, shutil
sys.stdout.reconfigure(encoding="utf-8")
ROOT=pathlib.Path.home()/"Music Studio"/"Integrations"/"OpenUtau-QA129"
ARCHIVE=ROOT/"Keiro_Revenant_v170.zip"
EXPECTED="a939d699d7d21cf4668a025224eee84cbe201da232968721c38bb6903f51d6cd"
assert ARCHIVE.is_file()
digest=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
assert digest==EXPECTED,(digest,EXPECTED)
DEST=ROOT/"portable"/"Singers"/"Keiro_Revenant_v170"
assert not (DEST/"files"/"acoustic.onnx").exists() or (DEST/"files"/"acoustic.onnx").stat().st_size>=190*1024*1024, "Unexpected existing model file"
DEST.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(ARCHIVE) as z:
 infos=z.infolist()
 assert len(infos)>80
 assert sum(i.file_size for i in infos)<750*1024*1024
 for item in infos:
  relative=pathlib.PurePosixPath(item.filename)
  assert not relative.is_absolute() and ".." not in relative.parts,item.filename
  assert not (item.external_attr>>16)&0o170000==0o120000, item.filename
  target=DEST.joinpath(*relative.parts)
  assert target.resolve().is_relative_to(DEST.resolve())
  if item.is_dir():target.mkdir(exist_ok=True);continue
  target.parent.mkdir(parents=True,exist_ok=True)
  with z.open(item) as inp, target.open("wb") as out:shutil.copyfileobj(inp,out,1024*1024)
cfg=DEST/"configs"/"character.yaml"
assert cfg.is_file() and (DEST/"files"/"acoustic.onnx").stat().st_size>190*1024*1024
character=DEST/"configs"/"character.txt"
assert character.is_file()
if character.stat().st_size==0:
 character.write_text("name=Keiro Revenant v170\n",encoding="utf-8")
assert (DEST/"tgm_hifigan"/"tgm_hifigan_v110.onnx").is_file()
manifest={"status":"installed_in_isolated_portable_OpenUtau","name":"Keiro Revenant v170",
"source":"Official LUNAI Project GitHub release 170","sha256":digest,
"internal_config":str(cfg),"singer_config_folder":str(cfg.parent),
"language":"ru","model_acoustic":str(DEST/"files"/"acoustic.onnx"),
"vocoder_bundled":True,"license":"Noncommercial only; attribution required. Cannot train other models with model outputs.",
"model_modified":False,"metadata_character_txt_initialized":True,
"installed_model_used_for_owner_voice_training":False,"production_music_studio_modified":False}
(ROOT/"qa129_keiro_install.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print("KEIRO_VERIFIED_INSTALLED",str(cfg),flush=True)
