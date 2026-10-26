from pathlib import Path
import json,hashlib,os,uuid,sys
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio";D=R/"Integrations"/"RapFullTrack-QA135"
result_path=D/"QA135_final_report.json"
result=json.loads(result_path.read_text(encoding="utf8"))
diction=json.loads((D/"QA135_diction_comparison.json").read_text(encoding="utf8"))
ratio=diction["comparison"]["source_vs_converted_token_sequence_similarity"]
assert ratio<.90
dest=Path(result["library_mp3"])
metadata=dest.with_suffix(".track.json")
existing=json.loads(metadata.read_text(encoding="utf8"))
assert existing["voice_preset_id"]=="qa133_consonant_protection_apexsvc"
note=("Фонемное качество ещё требует проверки на слух: локальный Whisper распознал "
 "часть слов в обработанном вокале иначе, чем в исходном. "
 "Сходство последовательностей распознанных слов ~%.1f%%; это приблизительная метрика, "
 "не оценка совпадения тембра. Оригинальная версия сохранена отдельно." %(ratio*100))
existing["voice_check_status"]="warning"
existing["voice_check_note"]=note
existing["acoustic_quality_verified"]=False
existing["asr_lexical_retentation_comparison"]={"approx_whisper_source_to_new_ratio":ratio,
   "not_exact_word_accuracy_or_stress_rating":True,"separate_raw_track_available":True}
backup=D/"QA135_track_metadata_before_ASR_warning.json"
if not backup.exists():backup.write_text(metadata.read_text(encoding="utf8"),encoding="utf8")
temp=metadata.with_name(metadata.name+"."+uuid.uuid4().hex+".tmp")
temp.write_text(json.dumps(existing,ensure_ascii=False,indent=2),encoding="utf8")
os.replace(temp,metadata)
vcpath=dest.with_suffix(".voicecheck.json")
qc=json.loads(vcpath.read_text(encoding="utf8"))
qc["status"]="warning";qc["reason"]=note
vcpath.write_text(json.dumps(qc,ensure_ascii=False,indent=2),encoding="utf8")
result["approx_whisper_lexical_similarity_source_to_conversion"]=ratio
result["diction_requires_listening"]=True
result["warnings"].append("Automatic speech recognizer detected lexical changes after voice conversion.")
result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
assert hashlib.sha256(dest.read_bytes()).hexdigest()==result["final_mp3_sha256"]
print("QA135_ASR_WARNING_SAVED",round(ratio,3),"AUDIO_UNCHANGED",flush=True)
