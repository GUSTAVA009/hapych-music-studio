"""Stable, reversible beat-production hints for ACE-Step music captions.
Adds genre-aware production instructions, not neural-network training.
"""
import re

HINTS = [
    (r"регги|рагга|dancehall|ragga|oriental|восточ|дарбук", "syncopated dancehall-reggae drum groove, swung offbeat percussion, punchy tight snare, darbuka fills, deep controlled sub-bass"),
    (r"trap|трэп|drill|дрилл", "modern trap beat, tuned 808 sub-bass, clear punchy kick, sharp snare and hi-hat subdivisions, coherent syncopation"),
    (r"рэп|rap|hip.?hop|хип.?хоп|пацан", "hip-hop instrumental production, strong steady kick-snare backbeat, groovy bassline, dry snare, articulate rhythmic pocket"),
    (r"club|клуб|dance|танцев|house|электро", "dancefloor-ready four-on-the-floor drums, sidechained bass, clean transient attack, professional dance mix"),
    (r"rock|рок|гитар|поп.?панк", "live drum kit with solid kick and snare, expressive bass guitar, realistic guitar rhythm, focused arrangement"),
    (r"pop|поп|припев|лирич|романтич", "modern pop production, melodic bass, tight organic drums, defined verse-chorus dynamics"),
]

BASE = ("radio-ready music production, coherent drums and bass locked to the same rhythm, "
        "clear separation of instruments, punchy transients, natural groove, "
        "musical arrangement with transitions, controlled low end, no clipping, no muddy mix")

def enhance_caption(style, bpm=0, enabled=True):
    style = str(style or "").strip()
    if not enabled:
        return style
    # In auto BPM mode, genre alone drives tempo: no hidden forced number.
    kind = ""
    for pattern, hint in HINTS:
        if re.search(pattern, style, flags=re.IGNORECASE):
            kind = hint
            break
    supplement = (kind + ", " if kind else "") + BASE
    if bpm:
        supplement = f"{int(bpm)} BPM, " + supplement
    room = max(0, 500 - len(supplement) - 3)
    return style[:room] + ". " + supplement if room else style[:500]


def prepare_lyrics(lyrics):
    """Preserve Russian spelling and punctuation; normalize line breaks/tags.
    Never rewrite syllables, phonemes or words on behalf of the singer.
    """
    import re
    lyrics = str(lyrics or "").replace("\r\n", "\n").replace("\r", "\n")
    lyrics = "\n".join(line.strip() for line in lyrics.split("\n"))
    lyrics = re.sub(r"\n{3,}", "\n\n", lyrics).strip()
    lyrics = re.sub(r"(?im)^\[(verse|chorus|bridge|intro|outro|pre-chorus|instrumental)(\s*\d*)\]\s*\n(?!\n)",
                    lambda m: "[" + m.group(1).title() + m.group(2) + "]\n", lyrics)
    if lyrics and "[" not in lyrics:
        lyrics = "[Verse 1]\n" + lyrics
    return lyrics


def enhance_vocal_clarity(caption, enabled=True):
    if not enabled:
        return caption
    hints = ("natural expressive Russian lead vocal, precisely articulated consonants and vowels, "
             "sung words rather than humming, clear diction, believable breathing and phrasing, "
             "respect commas and sentence endings, no gibberish")
    return (str(caption).strip() + ". " + hints)[:800]
