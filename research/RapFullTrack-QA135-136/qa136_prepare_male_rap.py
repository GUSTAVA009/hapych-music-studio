"""QA136: safe, read-only Music Studio preflight for a corrected all-male rap.
Original QA135 lyrics unchanged. No generation launched, no user files edited.
"""
from pathlib import Path
import sys,json,hashlib,requests
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio"
D=R/"Integrations"/"RapFullTrack-QA135"
base=json.loads((D/"QA135_rap_request.json").read_text(encoding="utf8"))
old=base["lyrics"]
changes={
 "[Verse 1 - deep male rhythmic rap flow, clear natural Russian consonants, punchy delivery]":"[Verse 1 - low male baritone spoken rap, firm native Russian consonants, dry chest voice]",
 "[Pre-Chorus - melodic sing-rap, synth build, drums rising]":"[Pre-Chorus - low male baritone rap, natural spoken rhythm, no vocal jump]",
 "[Chorus - catchy melodic male sing-rap hook, thick 808 bass, low backing harmonies]":"[Chorus - deep male baritone rap chant, same low male singer, chest register, rhythmic unison]",
 "[Verse 2 - low male rhythmic rap, double time cadence, heavy 808]":"[Verse 2 - deep male baritone rhythmic rap, same singer, no singing falsetto]",
 "[Bridge - half-time hip hop, intimate spoken male rap, airy keys]":"[Bridge - low male spoken rap, measured natural Russian timing]",
 "[Chorus - final energetic melodic rap hook, thick 808, low male harmonies]":"[Chorus - deep male baritone rap chant, same singer and register as verse, strong 808]",
 "[Male Adlibs - rhythmic natural Russian shouts]":"[Male Adlibs - low male baritone spoken rap]",
 "[Male Adlibs - soft background shouts]":"[Male Adlibs - only one low male voice, unison rap shouts]",
 "[Outro - soft low male spoken rap]":"[Outro - deep male spoken rap]"
}
for a,b in changes.items():
 assert a in old,("missing original tag",a)
 old=old.replace(a,b)
def words(t):
 return [x.strip() for x in t.splitlines() if x.strip() and not x.strip().startswith("[")]
assert words(old)==words(base["lyrics"])
assert len(words(old))>=40
style=(
 "Russian boom bap and trap rap, 96 BPM, 150 seconds. SOLO DEEP MALE BARITONE "
 "rapping ALL VERSES AND CHORUSES, same low chest register everywhere, native Russian "
 "spoken syllables, hard clear consonants. Low male RAP CHANT chorus, "
 "no octave jumps. Huge 808 sub bass, dry punchy kick and snare, "
 "tight hi-hats, muted Rhodes keys. Head-nod groove, confident "
 "syncopated rap flow, crisp diction, stable vocal placement; no backing choir, "
 "no high vocals, no falsetto, no female voices, no guitars."
)
assert len(style)<=512,len(style)
new=dict(base)
new.update({
 "title":"Громче, чем вчера — мужской рэп QA136",
 "style":style,"lyrics":old,"bpm":96,"duration":150,
 "two_versions":True,"apply_voice":False,
 "use_voice":True,"voice_profile_id":"",
 "use_trained_groove_reference":True})
dest=D/"QA136_AllMaleRap_Candidate.json"
dest.write_text(json.dumps(new,ensure_ascii=False,indent=2),encoding="utf8")
s=requests.Session();s.trust_env=False
response=s.post("http://127.0.0.1:7870/api/prepare",json=new,timeout=25)
print("QA136_PREFLIGHT_HTTP",response.status_code,flush=True)
assert response.status_code==200,response.text[:400]
p=response.json()
assert p["vocal_language"]=="ru"
assert "rock" not in p["caption"].lower()
assert p["style_plan"].get("genres") and all("rock" not in x for x in p["style_plan"]["genres"])
assert "Громче, чем вчера!" in p["lyrics"]
assert "Моё сердце ещё поёт!" in p["lyrics"]
assert "[Chorus - male vocal, baritone]" in p["lyrics"] and "[Verse 1 - male vocal, baritone, spoken word]" in p["lyrics"]
assert len(p["caption"])<=512
report={
 "status":"safe_preflight_only_not_submitted",
 "title":new["title"],
 "sung_lines_preserved_exactly":words(old)==words(base["lyrics"]),
 "lyrics_lines":len(words(old)),
 "genre_plan":p["style_plan"].get("genre_families",[]),
 "bpm":96,"seconds":150,
 "male_rap_verse_and_chorus_tags":True,
 "low_voice_unchanged_through_hook":True,
 "model_may_ignore_gender_instructions":True,
 "voice_protection_preset_separate":str(R/"Voice Profiles"/"presets"/"QA133_ConsonantProtection_ApexSVC.json"),
 "not_submitted_due_to_active_user_GPU_work":True,
 "request_path":str(dest),
 "caption_sent_if_generated":p["caption"],
 "request_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
 "production_studio_unmodified":True}
(D/"QA136_male_rap_preflight.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print("QA136_SAFELY_PREPARED",dest,flush=True)
print("QA136_GENRE",report["genre_plan"],"MALE_CHORUS",report["male_rap_verse_and_chorus_tags"],flush=True)
