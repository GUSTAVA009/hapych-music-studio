import json,yaml,pathlib,re,sys
sys.stdout.reconfigure(encoding="utf-8")
R=pathlib.Path.home()/"Music Studio"/"Integrations"/"OpenUtau-QA129"
D=R/"QA129_Score"
doc=json.loads((D/"QA129_phones.json").read_text(encoding="utf-8"))
for x in doc["syllables"]:
 if x["line"]==3:
  print("IPA",x["word"],x["syllable"],x["phonemes_ipa"],x["stressed"],x["tick"])
for p in (D/"QA129_Keiro_RussianDiffSinger.ustx",D/"QA129_Keiro_RussianDiffSinger-autosave.ustx"):
 proj=yaml.safe_load(p.read_text(encoding="utf-8"))
 print("USTX",p.name,"TRACK",proj["tracks"][0]["phonemizer"])
 for i,n in enumerate(proj["voice_parts"][0]["notes"]):
  if 7800<n["position"]<10300:
   print("NOTE",i,n["lyric"],n["position"],n["duration"],"overrides",n.get("phoneme_overrides"))
bank=R/"portable"/"Singers"/"Keiro_Revenant_v170"
for p in [bank/"files"/"dictionary-ru.txt",bank/"configs"/"dsdur"/"dsdict-ru-lunai.yaml",bank/"configs"/"dsdur"/"dsdict-ru.yaml"]:
 t=p.read_text(encoding="utf-8",errors="replace")
 print("DICT",p.name,"BYTES",len(t),"MATCHES",len(re.findall(r"(?im)^.*(?:когда|k o g d a|k a g d a).*?$",t)))
 print(*re.findall(r"(?im)^.*(?:когда|k o g d a|k a g d a).*?$",t)[:12],sep="\n")
print("DS_PHONES_START")
for f in ("phonemes.json","phonemes-variance.json"):
 p=bank/"files"/f
 arr=json.loads(p.read_text(encoding="utf-8"))
 print(f,type(arr).__name__,str(arr)[:1400])
