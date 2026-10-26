from pathlib import Path
import json,yaml
R=Path.home()/"Music Studio"/"Integrations"/"OpenUtau-QA129"
D=R/"QA132-KogdaPronunciation"
source=yaml.safe_load((R/"QA129_Score"/"QA129_Keiro_RussianDiffSinger.ustx").read_text(encoding="utf8"))
words=list(dict.fromkeys(note["lyric"] for note in source["voice_parts"][0]["notes"] if note["lyric"] not in ("+","-")))
assert "Когда" in words and "Сохрани" in words
assert len(words)>10
(D/"QA132_words_for_G2P.json").write_text(json.dumps(words,ensure_ascii=False,indent=2),encoding="utf8")
print("QA132_WORDS_FOR_G2P",len(words),flush=True)
