"""Create user-requested full Russian rap remake from the latest saved Music Studio
lyrics, preserving every sung word. Store selected QA133 consonant-protection
voice-transfer settings as a separate, reversible preset. No production edits.
Preflight the actual live Music Studio /api/prepare before generation.
"""
from pathlib import Path
import json,re,hashlib,sys,requests,time
sys.stdout.reconfigure(encoding="utf8")
ROOT=Path.home()/"Music Studio"
OUT=ROOT/"Integrations"/"RapFullTrack-QA135"
OUT.mkdir(parents=True,exist_ok=True)
sessions=sorted((ROOT/"Исходные версии").glob("*.session.json"),key=lambda p:p.stat().st_mtime,reverse=True)
assert sessions
session_file=sessions[0]
session=json.loads(session_file.read_text(encoding="utf8"))
past=session["requested"]
lyrics=past["lyrics"]
assert "Вечный шум и вечный бег" in lyrics
assert "Громче, чем вчера!" in lyrics
assert "Моё сердце ещё поёт!" in lyrics
assert len(lyrics.splitlines())>=60
tags={
 "[Intro - Distorted Electric Guitar Riff, Live Drums]":"[Intro - sparse Rhodes chords, airy synth pad, low 808 swell, rolling hi hats]",
 "[Male Shout]":"[Male Adlibs - rhythmic natural Russian shouts]",
 "[Verse 1 - Deep Male Baritone, Driving Rock]":"[Verse 1 - deep male rhythmic rap flow, clear natural Russian consonants, punchy delivery]",
 "[Pre-Chorus - Rising Male Vocals, Guitar Build]":"[Pre-Chorus - melodic sing-rap, synth build, drums rising]",
 "[Chorus - Explosive Male Rock Vocals, Heavy Guitar]":"[Chorus - catchy melodic male sing-rap hook, thick 808 bass, low backing harmonies]",
 "[Male Backing Vocals]":"[Male Adlibs - soft background shouts]",
 "[Verse 2 - Raspy Male Voice, Heavy Bass]":"[Verse 2 - low male rhythmic rap, double time cadence, heavy 808]",
 "[Instrumental Break - Electric Guitar Solo, Punchy Drums]":"[Instrumental Break - instrumental 808, crisp claps, subtle Rhodes piano solo]",
 "[Bridge - Half-Time Drums, Emotional Male Voice]":"[Bridge - half-time hip hop, intimate spoken male rap, airy keys]",
 "[Short Silence]":"[Break - short silence for beat drop]",
 "[Final Chorus - Full Band, Layered Male Harmonies]":"[Chorus - final energetic melodic rap hook, thick 808, low male harmonies]",
 "[Outro - Guitar Power Chord, Drum Crash]":"[Outro - sparse Rhodes chord, 808 tail, gentle reverb fade]",
 "[Deep Male Voice]":"[Outro - soft low male spoken rap]"
}
for old,new in tags.items():
 assert old in lyrics,("Original heading not found",old)
 lyrics=lyrics.replace(old,new)
def sung(t):
 return [x.strip() for x in t.splitlines() if x.strip() and not x.strip().startswith("[")]
assert sung(lyrics)==sung(past["lyrics"]),"Sung words changed"
assert len(lyrics)<4000
style=("Modern Russian melodic rap, trap hip-hop, 100 BPM, 150 seconds. "
 "Deep warm male baritone; clear conversational Russian rap in verses, confident flow, "
 "catchy smooth melodic sing-rap in chorus. Natural native Russian stress and intact consonants. "
 "Huge tuned 808 sub bass, tight hip-hop kick, crisp claps, rolling hi-hats, "
 "warm Rhodes piano, airy synth pads, understated bell motif. "
 "Half-time bridge, big final hook. "
 "Clean warm lead upfront, punchy wide studio mix. No female vocals or harsh autotune.")
assert len(style)<=512,len(style)
ref=ROOT/"Мой голос"/"20261022_234327_Микрофон_3867cb.wav"
assert ref.is_file()
assert hashlib.sha256(ref.read_bytes()).hexdigest()=="4486fc6a306446c139ace134672ea9ad7054b72ed8da681d03dcce1ae1498d1f"
requested=dict(past)
requested.update({
 "title":"Громче, чем вчера — рэп",
 "style":style,"lyrics":lyrics,
 "bpm":100,"duration":150,
 "instrumental":False,"two_versions":False,
 "russian_rap":True,
 "use_voice":True,"voice":ref.name,"voice_profile_id":"",
 "apply_voice":False,
 "style_reference":False,
 "use_trained_groove_reference":True,
 "mode":"new","source":"",
 "voice_register":"auto"})
assert requested["style"] and requested["lyrics"]
preset={
 "id":"qa133_consonant_protection_apexsvc",
 "label":"Мой тембр — защита согласных QA133",
 "version":"1.0",
 "source":"QA133_Consonants user-selected follow-up",
 "engine":"ApexSVC zero-shot",
 "parameters":{"topk":6,"alpha":.32,"protect":.88,"rms_mix_rate":.95,
               "f0_method":"fcpe","f0_filter_radius":3,
               "pitch_shift_semitones":0.0,"autotune_strength":0,
               "vad_trim_reference":True},
 "references":[
 {"file":"20261022_234327_Микрофон_3867cb.wav","sha256":"4486fc6a306446c139ace134672ea9ad7054b72ed8da681d03dcce1ae1498d1f"},
 {"file":"20261022_183309_Микрофон_df413d.wav","sha256":"f5751ba2ae6a648a164660ad43e48be4b0eb1261772245e5f5696ca333dd9ba4"}],
 "processing":"Isolate vocal stem, apply Apex to vocals only, then remix to untouched instrumental; produce separate new master",
 "voice_quality":"QA133 showed 3/4 line-exact Whisper transcription, not certified one-to-one timbre",
 "production_default_changed":False,
 "use_in_this_project":True,
 "no_other_singer_training":True,
 "no_source_overwrite":True,
 "song_title":requested["title"]}
preset_dest=ROOT/"Voice Profiles"/"presets"/"QA133_ConsonantProtection_ApexSVC.json"
preset_dest.parent.mkdir(parents=True,exist_ok=True)
preset_dest.write_text(json.dumps(preset,ensure_ascii=False,indent=2),encoding="utf8")
request_path=OUT/"QA135_rap_request.json"
request_path.write_text(json.dumps(requested,ensure_ascii=False,indent=2),encoding="utf8")
s=requests.Session();s.trust_env=False
url="http://127.0.0.1:7870"
health=s.get(url+"/api/health",timeout=8).json()
assert health["ready"]
assert health["job"]["status"] not in ("preparing","generating","converting"),health["job"]["status"]
preview=s.post(url+"/api/prepare",json=requested,timeout=30)
print("QA135_PREFLIGHT_HTTP",preview.status_code,flush=True)
if preview.status_code!=200:raise RuntimeError(preview.text[:500])
prep=preview.json()
assert prep["vocal_language"]=="ru",prep["vocal_language"]
assert len(prep["caption"])<=512,len(prep["caption"])
assert "rock" not in prep["style_plan"].get("genre_families",[]) and "rock" not in prep["style_plan"].get("genres",[]),prep["style_plan"]
assert prep.get("duration_seconds",150)==150,prep.get("duration_seconds")
assert "Вечный шум и вечный бег" in prep["lyrics"]
assert "Громче, чем вчера!" in prep["lyrics"]
assert "Моё сердце ещё поёт!" in prep["lyrics"]
info={"status":"prepared_validated",
 "request_file":str(request_path),"saved_preset":str(preset_dest),
 "source_session":str(session_file),
 "original_sung_lines":len(sung(past["lyrics"])),
 "lyrics_words_identical_to_last_studio_session":True,
 "duration_seconds":150,"bpm":100,"rap_style":style,
 "voice_reference_for_register_only":ref.name,
 "production_voice_conversion_disabled_in_primary_generation":True,
 "QA133_consonant_preset_to_apply_post_gen":True,
 "voice_profile_database_untouched":True,
 "human_audio_not_yet_verified":True,
 "preview_caption":prep["caption"],"style_plan":prep["style_plan"],
 "preflight_warnings":prep.get("warnings",[])[:12]}
(OUT/"QA135_preflight_report.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding="utf8")
print("QA135_PREFLIGHT_OK","SUNG_LINES",info["original_sung_lines"],"STYLE",prep["caption"][:100],flush=True)
print("QA135_SAVED_PRESET",preset_dest,flush=True)
