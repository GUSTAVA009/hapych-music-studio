"""Deterministic lyric/director separation and auditable caption preparation.
No speech/phoneme synthesis or guarantee of acoustic pronunciation is implied.
Original inputs, omissions and exact model inputs remain available to the UI.
"""
from __future__ import annotations
import html
import re
from typing import Any

CAPTION_LIMIT = 512
LYRICS_LIMIT = 4096
SECTION_PATTERNS = [
    (r"final\s+chorus|финальн\w*\s+припев", "Chorus", "финальный припев"),
    (r"pre[ -]?chorus|пред[ -]?припев|распев", "Pre-Chorus", ""),
    (r"spoken\s+intro", "Intro", "разговорное вступление"),
    (r"instrumental\s+break|instrumental|interlude|инструментал\w*|проигрыш|интерлюдия|solo|соло", "Instrumental", ""),
    (r"verse|куплет", "Verse", ""),
    (r"chorus|припев", "Chorus", ""),
    (r"bridge|бридж|мост", "Bridge", ""),
    (r"intro|интро|вступление", "Intro", ""),
    (r"outro|аутро|завершение|кода", "Outro", ""),
    (r"end|конец", "End", ""),
    (r"drop|дроп", "Drop", ""),
    (r"breakdown|брейкдаун", "Breakdown", ""),
]
# Phrase-level glossary, not a general translation model. Unmatched text is kept.
GLOSSARY = [
    (r"catchy Russian summer resort pop", "летний курортный поп", 10),
    (r"beautiful warm sensual feminine voice", "тёплый чувственный голос", 11),
    (r"playful southern Russian seaside intonation", "южное игривое настроение", 17),
    (r"expressive melodic singing", "выразительное мелодичное пение", 22),
    (r"sunny Black Sea vacation atmosphere", "солнечное черноморское лето", 35),
    (r"romantic coastal dance pop", "романтичный танцевальный поп", 15),
    (r"tropical house influences", "тропикал-хаус", 12),
    (r"catchy accordion melody", "аккордеон", 16),
    (r"rhythmic acoustic Spanish guitar", "испанская гитара", 16),
    (r"groovy warm bass", "упругий бас", 16),
    (r"clean punchy dance kick", "чёткий танцевальный бит", 16),
    (r"crisp percussion", "перкуссия", 16),
    (r"subtle saxophone fills", "мягкий саксофон", 16),
    (r"shimmering synths", "воздушные синтезаторы", 16),
    (r"sea breeze ambience", "шум моря", 19),
    (r"seaside promenade at sunset", "закат у моря", 35),
    (r"joyful romantic energy", "радостная романтика", 35),
    (r"addictive sing-along chorus", "цепкий напевный припев", 18),
    (r"wide female vocal harmonies", "женские бэк-вокалы", 17),
    (r"polished radio-ready studio production", "чистое сведение", 30),
    (r"strong melodic hook", "цепкая мелодия", 30),
    (r"dynamic chorus drop", "контрастный припев", 30),
    (r"natural musical pauses", "естественные паузы", 22),
    (r"no rap", "без рэпа", 5),
    (r"no robotic voice", "без роботизации", 25),
    (r"no excessive autotune", "без сильного автотюна", 6),
]
LANGUAGE_TERMS = re.compile(r"^(?:natural native Russian pronunciation|correct word stress|clear vocal articulation|русское произношение|правильные ударения)$", re.I)
GENDER_TERMS = re.compile(r"^(?:(?:female|male)(?: lead)? vocals?(?: ONLY)?|no (?:male|female) vocals|только (?:женский|мужской) вокал)$", re.I)


def clean_markup(value: str) -> str:
    text = html.unescape(str(value or "")).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = text.replace("\ufeff", "").replace("\u200b", "").replace("\xa0", " ")
    text = re.sub(r"\\([*_[\]`])", r"\1", text)
    text = re.sub(r"\\[ \t]*(?=\n|$)", "", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"(?m)^\s*```[^\n]*$", "", text)
    return text


def split_header(content: str) -> tuple[str | None, str]:
    content = content.strip()
    for pattern, name, extra in SECTION_PATTERNS:
        match = re.match(r"^(?:" + pattern + r")(?=\s|\d|[-—–:;,]|$)\s*(\d+)?", content, re.I)
        if match:
            number = match.group(1)
            tag = name + (" " + number if number and name == "Verse" else "")
            suffix = content[match.end():].strip(" \t—–-:;,.")
            direction = "; ".join(x for x in (extra, suffix) if x)
            return tag, direction
    return None, content


def parse_lyrics(value: str) -> dict[str, Any]:
    text = clean_markup(value)
    directions: list[dict[str, Any]] = []
    output: list[str] = []
    current = "Общее"
    for line_number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if re.fullmatch(r"[\\*`_\s]*", line):
            output.append("")
            continue
        line = re.sub(r"^#{1,6}\s+", "", line)
        # Unbalanced standalone headers are quarantined instead of sung.
        if line.startswith("[") and "]" not in line:
            directions.append({"section": current, "text": line[1:], "line": line_number, "unparsed": True})
            continue
        def bracket(match: re.Match[str]) -> str:
            nonlocal current
            tag, instruction = split_header(match.group(1))
            if tag:
                current = tag
            if instruction:
                directions.append({"section": current, "text": instruction, "line": line_number, "unparsed": tag is None})
            return "\n[" + tag + "]\n" if tag else ""
        if "[" in line:
            line = re.sub(r"\[([^\[\]]*)\]", bracket, line)
        else:
            # Also accept standalone Russian/English header lines with a colon/dash.
            tag, instruction = split_header(line)
            plain_header = tag and (not instruction or re.search(r"[—–:]|\s-\s", line))
            if plain_header:
                current = tag
                if instruction:
                    directions.append({"section": tag, "text": instruction, "line": line_number, "unparsed": False})
                line = "[" + tag + "]"
        output.append(line)
    lyric = "\n".join(output)
    lyric = "\n".join(x.strip() for x in lyric.splitlines())
    lyric = re.sub(r"\n{3,}", "\n\n", lyric).strip()
    if lyric and not re.search(r"(?m)^\[", lyric):
        lyric = "[Verse 1]\n" + lyric
    if len(lyric) > LYRICS_LIMIT:
        raise ValueError("После очистки текст длиннее 4096 символов. Раздели песню на части: слова не обрезаются.")
    return {"lyrics": lyric, "directions": directions, "changed": lyric != str(value or "").strip()}


def infer_gender(text: str, requested: str = "auto") -> str:
    if requested in ("female", "male"):
        return requested
    # Strip negative constraints before recognizing the requested performer.
    positive = re.sub(r"\bno\s+(?:male|female)\s+vocals?\b|без\s+(?:мужск|женск)\w*\s+вокал\w*", "", text, flags=re.I)
    female = bool(re.search(r"\bfemale\b|feminine|женск\w*\s+(?:голос|вокал|бэк)", positive, re.I))
    male = bool(re.search(r"\bmale\b|masculine|мужск\w*\s+(?:голос|вокал)", positive, re.I))
    return "female" if female and not male else "male" if male and not female else "auto"


def direction_summaries(directions: list[dict[str, Any]]) -> list[str]:
    # Only descriptions understood by this deterministic mapper go into the caption.
    # All original descriptions remain separately visible, including unmapped ones.
    by_section: dict[str, list[str]] = {}
    for entry in directions:
        raw = entry["text"].lower()
        words = []
        for pattern, cue in [
            (r"шум моря|ocean|sea\s+(?:waves|ambience)", "шум моря"),
            (r"нежн|gentle|soft", "нежно"),
            (r"ш[её]пот|whisper", "почти шёпотом"),
            (r"затухан|fade", "затухание"),
            (r"нараста|подъ[её]м|build", "нарастание"),
            (r"игрив|playful|улыбк", "игриво"),
            (r"энергич|мощн|ярк|полный бит|energetic", "энергично"),
            (r"бэк|harmon", "бэк-вокал"),
        ]:
            if re.search(pattern, raw):
                words.append(cue)
        if words:
            bucket = by_section.setdefault(entry["section"], [])
            bucket.extend(x for x in words if x not in bucket)
    order = {"Intro": 0, "Bridge": 1, "Outro": 2, "Chorus": 3, "Pre-Chorus": 4}
    return [key + ": " + ", ".join(by_section[key]) for key in sorted(by_section, key=lambda k: order.get(k, 5))]


def prepare_request(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Нужен объект параметров песни.")
    raw_style = str(data.get("style", "")).strip()
    raw_lyrics = str(data.get("lyrics", ""))
    if len(raw_style) > 12000 or len(raw_lyrics) > 24000:
        raise ValueError("Слишком большой исходный текст: стиль до 12000, текст до 24000 символов.")
    if not raw_style:
        raise ValueError("Укажи музыкальный стиль.")
    instrumental = bool(data.get("instrumental", False))
    parsed = parse_lyrics(raw_lyrics) if not instrumental else {"lyrics": "[Instrumental]", "directions": [], "changed": False}
    style = re.sub(r"\s+", " ", clean_markup(raw_style)).strip()
    context = style + " " + " ".join(x["text"] for x in parsed["directions"])
    gender = infer_gender(context, str(data.get("vocal_gender", "auto")))
    requested_lang = str(data.get("vocal_language", "ru"))
    if requested_lang not in ("ru", "auto", "en"):
        raise ValueError("Поддерживаемые настройки языка: ru, en, auto.")
    language = "unknown" if instrumental else ("ru" if requested_lang == "auto" and re.search(r"[А-Яа-яЁё]", parsed["lyrics"]) else "unknown" if requested_lang == "auto" else requested_lang)
    no_rap = bool(re.search(r"\bno\s+rap\b|без\s+рэпа", context, re.I))
    candidates: list[tuple[int, int, str, str]] = []
    serial = 0
    def add(text: str, priority: int, origin: str) -> None:
        nonlocal serial
        text = text.strip(" .;,")
        if text:
            candidates.append((priority, serial, text, origin))
            serial += 1
    if not instrumental:
        if language == "ru":
            add("Песня на русском, чёткая дикция и естественные ударения", 0, "Язык вокала")
        elif language == "en":
            add("English lyrics, natural English diction", 0, "Язык вокала")
        if gender != "auto":
            add("Только женский вокал" if gender == "female" else "Только мужской вокал", 1, "Голос")
    else:
        add("Инструментальная музыка без вокала", 0, "Режим")
    terms = [x.strip(" .") for x in re.split(r"[,;\n]+", style) if x.strip(" .")]
    replacements = []
    for index, term in enumerate(terms):
        if language == "ru" and LANGUAGE_TERMS.fullmatch(term):
            replacements.append({"original": term, "compact": "Русское произношение и ударения"})
            continue
        if gender != "auto" and GENDER_TERMS.fullmatch(term):
            replacements.append({"original": term, "compact": "Только женский вокал" if gender == "female" else "Только мужской вокал"})
            continue
        mapped = next(((compact, priority) for pattern, compact, priority in GLOSSARY if re.fullmatch(pattern, term, re.I)), None)
        if mapped:
            compact, priority = mapped
            add(compact, priority, term)
            replacements.append({"original": term, "compact": compact})
        else:
            priority = 9 if index == 0 else 14
            if re.search(r"\bBPM\b|тональн|minor|major|без |\bno\b|\bonly\b", term, re.I):
                priority = 4
            add(term, priority, term)
    for cue in direction_summaries(parsed["directions"]):
        add(cue, 13 if cue.startswith(("Intro:", "Bridge:", "Outro:")) else 28, "Указание: " + cue)
    selected, omitted, seen = [], [], set()
    for _, _, text, origin in sorted(candidates):
        key = text.casefold().rstrip(".")
        if key in seen:
            continue
        proposed = "; ".join(selected + [text])
        if len(proposed) <= CAPTION_LIMIT:
            selected.append(text)
            seen.add(key)
        else:
            omitted.append({"original": origin, "compact": text})
    # For one huge prose clause retain whole words, explicitly list the remainder.
    if len(selected) <= 2 and terms and len(terms[0]) > CAPTION_LIMIT:
        room = CAPTION_LIMIT - len("; ".join(selected)) - 2
        prefix = terms[0][:max(0, room)].rsplit(" ", 1)[0]
        if prefix:
            selected.append(prefix)
    caption = "; ".join(selected)
    if not caption:
        raise ValueError("Не удалось подготовить музыкальное описание.")
    warnings = []
    if parsed["directions"]:
        warnings.append("Пояснения из квадратных скобок отделены от слов песни. Точное исполнение звуковых эффектов и указаний по разделам зависит от модели.")
    if omitted:
        warnings.append("Не все детали вместились в 512 символов. Ниже показаны точное задание и исключённые детали; исходное описание сохранено.")
    if any(x["unparsed"] for x in parsed["directions"]):
        warnings.append("Есть нестандартные указания: они показаны в плане, но не отправлены как слова для пения.")
    if gender == "female" and data.get("use_voice"):
        warnings.append("Запрошен женский вокал, но включён перенос тембра записи. Для самостоятельного женского вокала отключи «Мой голос»; пол записи автоматически не определяется.")
    if no_rap and data.get("russian_rap"):
        warnings.append("В задании указан запрет рэпа: рэп-LoRA будет отключена для этой генерации.")
    if re.search(r"\b[A-Za-z]{3,}\b", re.sub(r"\[[^\]]*\]", "", parsed["lyrics"])) and language == "ru":
        warnings.append("В словах есть латиница. Русские слова лучше писать кириллицей; IPA и фонемная транскрипция здесь не интерпретируются автоматически.")
    return {
        "lyrics": parsed["lyrics"], "caption": caption, "directions": parsed["directions"],
        "vocal_language": language, "vocal_gender": gender, "no_rap": no_rap,
        "raw_style": raw_style, "raw_lyrics": raw_lyrics,
        "style_original_length": len(raw_style), "caption_length": len(caption),
        "lyrics_length": len(parsed["lyrics"]), "changed_lyrics": parsed["changed"],
        "replacements": replacements, "omitted": omitted, "warnings": warnings,
        "negative_prompt": "foreign-accented Russian, anglicized vowels, broken held notes, pitch flutter, exaggerated vibrato, unintelligible syllables, sung stage directions" if language == "ru" else "NO USER INPUT",
        "version": "1.4",
    }
