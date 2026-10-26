from pathlib import Path
import hashlib, json, re
import soundfile as sf
R=Path.home()/"Music Studio"/"Integrations"/"OpenUtau-QA129"
D=R/"QA132-KogdaPronunciation"
asr=json.loads((D/"QA132_asr_report.json").read_text(encoding="utf8"))
audio=json.loads((D/"QA132_audio_comparison_report.json").read_text(encoding="utf8"))
g2p=json.loads((D/"QA132_caseguard_report.json").read_text(encoding="utf8"))
src=R/"QA129_Score"/"QA129_Keiro_RussianDiffSinger.ustx"
assert hashlib.sha256(src.read_bytes()).hexdigest()==g2p["source_ustx_sha256"]
assert audio["status"]=="QA132_four_phrases_audio_assembled" and len(audio["stems"])==4
assert [round(x["WER"],3) for x in asr["line_results"]]==[0,0,.2,.333]
raw=(D/"QA132_headless_phoneme_audit.log").read_bytes()
audit=raw.decode("utf-16") if raw[:2] in (b"\xff\xfe",b"\xfe\xff") else raw.decode("utf-8",errors="replace")
phrase=re.search(r"QA132_PHRASE_3_PHONEMES=(.*)",audit)
assert phrase is not None
assert phrase.group(1).split()[:5]==["ru/k","ru/A","ru/g","ru/d","ru/a"]
for fn in (
 "QA132_Keiro_RussianCaseGuard.ustx","QA132_Listen_AB.html",
 "QA132_RussianPronunciation_Corrected_21s.wav",
 "QA132_RussianPronunciation_Corrected_21s.mp3",
 "QA132_When_OLD_ka_gda.wav","QA132_When_OLD_ka_gda.mp3",
 "QA132_When_NEW_ka_gda.wav","QA132_When_NEW_ka_gda.mp3"):
 assert (D/fn).exists(),fn
assert abs(sf.info(D/"QA132_RussianPronunciation_Corrected_21s.wav").duration-20.88)<.01
report={
 "status":"QA132_audio_rendered_isolated_not_released",
 "runtime_phonemes_for_kogda":"ru/k ru/A ru/g ru/d ru/a",
 "runtime_vowel_reduction_confirmed":True,
 "original_lyrics_preserved":True,
 "31_notes_unchanged":True,
 "source_project_sha256_unchanged":True,
 "new_full_audio_wav":"QA132_RussianPronunciation_Corrected_21s.wav",
 "new_full_audio_mp3":"QA132_RussianPronunciation_Corrected_21s.mp3",
 "old_new_phrase_mp3":["QA132_When_OLD_ka_gda.mp3","QA132_When_NEW_ka_gda.mp3"],
 "listening_page":"QA132_Listen_AB.html",
 "automated_asr_WER_lines":[x["WER"] for x in asr["line_results"]],
 "automated_asr_line_3":asr["line_results"][2]["recognized"],
 "automated_asr_line_4":asr["line_results"][3]["recognized"],
 "full_wer":asr["full_track_word_error_rate"],
 "issues":"Whisper recognizes дождь as тошть and мою as ему on this new sample; cannot infer Russian vowel quality or stress from ASR alone.",
 "human_listening_verified":False,
 "user_voice_conversion_done":False,
 "no_training_performed":True,
 "not_promoted_to_music_studio":True,
 "owner_voice_files_unchanged":True,
 "gpu_left_for_rust":True,
 "licensing":"Keiro Revenant (LUNAI Project) noncommercial audition only"
}
(D/"QA132_FINAL_VERDICT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print("QA132_FINAL_VERDICT_WRITTEN",report["status"],report["runtime_phonemes_for_kogda"],report["automated_asr_WER_lines"])
