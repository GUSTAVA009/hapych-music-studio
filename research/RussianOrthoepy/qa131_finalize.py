"""Finalize QA130/131 isolated comparison and safely remove only expendable
inference prep copies. Retain all final listening WAV/MP3 and project.
"""
from pathlib import Path
import json,hashlib,os,sys
sys.stdout.reconfigure(encoding="utf-8")
R=Path.home()/"Music Studio"
A=R/"Integrations"/"RussianOrthoepy"/"QA130-OwnerTimbre"
B=R/"Integrations"/"RussianOrthoepy"/"QA131-SoulX"
q=json.loads((A/"QA130_quality_report.json").read_text(encoding="utf-8"))
run=json.loads((B/"qa131_run_report.json").read_text(encoding="utf-8"))
assert run["status"]=="rendered_pending_QA"
assert len(q["results"])==3
assert all(not data["automated_gates"]["words_exact_per_line"] for data in q["results"].values())
assert q["no_production_changes"]
assert hashlib.sha256(Path(run["wav"]).read_bytes()).hexdigest()==run["sha256"]
refs={
 "20261022_234327_Микрофон_3867cb.wav":"4486fc6a306446c139ace134672ea9ad7054b72ed8da681d03dcce1ae1498d1f",
 "20261022_183309_Микрофон_df413d.wav":"f5751ba2ae6a648a164660ad43e48be4b0eb1261772245e5f5696ca333dd9ba4"}
for name,expected in refs.items():
 assert hashlib.sha256((R/"Мой голос"/name).read_bytes()).hexdigest()==expected
labels={"consonant_safe":"A — ApexSVC, consonant safe",
 "identity_focused":"B — ApexSVC, identity focused",
 "soulx":"C — SoulX-Singer, alternate architecture"}
summary={}
for tag,data in q["results"].items():
 summary[tag]={
  "label":labels[tag],"phrase_WER":[t["WER"] for t in data["word_error_lines"]],
  "owner_similarity_proxy":data["owner_similarity_proxy"],
  "owner_similarity_gain_vs_source":data["similarity_gain_vs_source"],
  "pitch_median_abs_cents":data["pitch"]["median_abs_cents"],
  "hard_dropouts_over70ms":data["audio"]["hard_dropouts_over70ms"],
  "full_track_WER":data["full_WER"],
  "automated_release_gate":False,
  "notes":"No human verification of Russian phonetic stress, singer similarity, smoothness or buzz."}
report={
 "status":"experimental_3_variants_created_not_promoted",
 "no_candidate_passed_strict_words_gate":True,
 "main_blocker":"last line 'Сохрани мою любовь' not reliable after owner voice conversion",
 "best_for_identity_proxy_only":"identity_focused",
 "best_for_line_word_preservation":"No winner; Apex A/B each exact on three of four lines",
 "soulx_tradeoff":"C modifies words in first/third/fourth lines, has less pitch fidelity than Apex",
 "noncommercial_source":"Keiro Revenant from LUNAI Project used only as synthetic audition source",
 "third_party_model_or_audio_trained_on":False,
 "microphone_recordings_untouched":True,"working_studio_modified":False,
 "user_voice_one_to_one_confirmed":False,"human_diction_confirmed":False,
 "preview":str(A/"QA130_Listen.html"),
 "cases":summary}
(A/"QA130_comparison_verdict.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
# QA131 prep copies are safe to re-generate. Keep final WAV, MP3, reports and source.
disposable=[B/"prompt.wav",B/"prompt_f0.npy",B/"target.wav",B/"target_f0.npy",B/"SoulX_Inference"/"generated.wav"]
reclaimed=0
for p in disposable:
 if p.exists():
  assert p.is_relative_to(B) and p.is_file()
  reclaimed+=p.stat().st_size
  p.unlink()
report["cleaned_temp_bytes"]=reclaimed
(A/"QA130_comparison_verdict.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
(B/"qa131_quality_verdict.json").write_text(json.dumps({"status":"rejected_for_production",
 "evaluation":summary["soulx"],"mic_source_untouched":True,
 "working_studio_untouched":True,"temp_bytes_cleaned":reclaimed},ensure_ascii=False,indent=2),encoding="utf-8")
print("QA130_COMPARISON_FINAL",json.dumps({"cases":{tag:{"WER_lines":r["phrase_WER"],
 "speaker":r["owner_similarity_proxy"],"pitch":r["pitch_median_abs_cents"]}for tag,r in summary.items()},
 "reclaimed_temp_MB":round(reclaimed/1024**2,2)},ensure_ascii=False),flush=True)
