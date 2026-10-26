"""Music Studio style compiler v30.
Loss-aware, dense 512-character ACE-Step caption. Every raw user instruction
is retained in the style plan; impossible-to-fit terms are surfaced, not hidden.
No claims that the model will honor every timbre or individual performer.
"""
from __future__ import annotations
import re
from prompt_director26 import compile_brief as previous, masked_positive, MAX, GENRES

def _has(p, text):
    return bool(re.search(p,text,re.I))
def _parts(s):
    return [x.strip(" .,-") for x in re.split(r"(?<=[.!?])\s+|[,;\n]+",s) if x.strip(" .,-")]

DETAILS=[
 ("dark 2000s urban crime noir",r"dark|crime|urban|noir|криминал|мрачн|городск"),
 ("GTA IV noir mood, GTA V punch",r"GTA\s*(?:IV|4|V|5)|grand theft auto"),
 ("emotional melancholy, tension",r"melanchol|эмоциональн|печаль|тоск|эмоцион"),
 ("cinematic development and strong musical climax",r"cinematic|cinema|epic|оркестров|кинематограф"),
 ("wide spacious stereo mix, defined depth",r"wide stereo|стерео|объ[её]мн|пространств|spacious|spatial"),
 ("clear present lead vocal above backing",r"clear vocals|разборчив|четк.*вокал|вокал.*вперед"),
 ("vinyl crackle texture",r"vinyl.*crackle|винилов|треск.*пластин"),
]
VOCALS=[
 ("connected melodic singing, warm male baritone, smooth register transitions",r"(?:continuous|connected|sustained|melodic|legato).{0,44}(?:singing|sung)|(?:sung|singing).{0,38}(?:baritone|melody|lead|verses?|chorus)|певуч|мелодическ.{0,20}(?:вокал|пени)"),
 ("deep baritone Russian male rap lead",r"male rap|мужск.*рэп|глубок.*мужск|deep baritone|baritone lead|low\s+(?:male\s+)?baritone|male\s+low\s+baritone"),
 ("raspy second voice",r"raspy|хрипл|gritty|втор.*голос"),
 ("tenor hook",r"tenor|тенор"),
 ("4 low male backing harmonies",r"(?:four|4)\s+low\s+male\s+(?:backing|background)\s+(?:harmon(?:y|ies)|vocals?|voices?|layers?)"),
 ("4 male backing vocal layers",r"(?:four|4)\s+(?:layered\s+)?(?:male\s+)?(?:backing|background)\s+(?:vocals?|voices?|harmon(?:y|ies)|layers?)|четыр[её]х?.*бэк"),
 ("call-response chants/adlibs",r"chant|ad-?libs?|call.and.response|перекличк|кричалк"),
 ("emotive spoken male narration",r"spoken|narration|речитатив|разговорн"),
 ("native Russian diction, sustained legato",r"native russian|russian diction|естественн.*русск|correct.*stress|правильн.*ударен"),
]
INSTRUMENTS=[
 ("ominous low strings",r"ominous.*string|low string|love string|струнн|(?:^|\W)strings?(?:\W|$)|cello|виолончел"),
 ("bright funky piano",r"(?:bright|funky).{0,25}piano|piano.{0,25}(?:bright|funky)|ярк.{0,20}пиан|фанков.{0,20}пиан"),
 ("dark melancholic piano",r"(?:dark|melanchol|noir|ominous).{0,25}piano|piano.{0,25}(?:dark|melanchol|noir)|мрачн.{0,20}пиан"),
 ("piano",r"пианино|фортепиано|(?<!\w)piano(?!\w)"),
 ("distorted electric guitar",r"distorted.*guitar|electric guitar|электрогитар|guitar riff"),
 ("smoky saxophone",r"smoky.*sax|sax(?:ophone)?|саксофон"),
 ("hard boom-bap drums",r"boom[ -]?bap|бум[ -]?бэп|hard drums|жестк.*бит"),
 ("punchy kick, snare and hi-hats",r"kick|snare|hi[ -]?hat|малый.*барабан"),
 ("huge 808 sub-bass",r"\b808\b|huge sub|глубок.*бас"),
 ("acoustic guitar",r"acoustic guitar|акустическ.*гитар"),
 ("synth pads",r"synth pad|синтезаторн.*пэд"),
 ("brass section",r"brass|трубы\s+оркестр"),
 ("live percussion",r"percussion|перкусси"),
 ("accordion",r"accordion|аккордеон"),
]
TECH=[
 ("92 BPM",r"\b92\s*BPM\b"), # An explicit tempo is handled dynamically below.
]
def summarize(style, prepared, base):
    positive=masked_positive(style)
    section_text="; ".join(str(i.get("text","")) for s in prepared.get("sections",[]) for i in s.get("instructions",[]))
    genre=list(base["style_plan"].get("genres",[]))
    # Unlike the original 2-genre selector, retain every explicitly named genre.
    all_genres=[];covered=[]
    for lab,pat,family in GENRES:
        m=re.search(pat,positive,re.I)
        if m:all_genres.append((m.start(),-len(m.group()),lab,family,m.end()))
    unique=[]
    for start,neglen,lab,family,end in sorted(all_genres):
        if any(start>=a and end<=b for a,b in covered):continue
        covered.append((start,end))
        if family not in [x[1] for x in unique]:unique.append((lab,family))
    if unique:genre=[v[0] for v in unique]
    elif _has(r"\bcinema\b|кинематограф|саундтрек",positive):genre=["cinematic orchestral"]
    plan=base["style_plan"]
    plan["all_requested_genres"]=genre
    tags={"genres":genre,"mood":[],"voices":[],"instruments":[],"rhythm":[],"mix":[],"other":[]}
    for value,p in DETAILS:
        if _has(p,positive):tags["mood" if "atmosphere" in value or "melancholy" in value else "mix"].append(value)
    for value,p in VOCALS:
        if _has(p,positive):tags["voices"].append(value)
    combined=positive+"; "+section_text
    if _has(r"(?:four|4)\s+(?:low\s+)?male.*(?:backing|background|harmon|voice|layer)|четыр.*мужск.*бэк",combined):
        item="4 low male backing harmonies" if _has(r"(?:four|4)\s+low\s+male",combined) else "4 male backing vocal layers"
        if item not in tags["voices"]:tags["voices"].append(item)
    for value,p in INSTRUMENTS:
        if value=="piano" and any(k in tags["instruments"] for k in ("bright funky piano","dark melancholic piano")):
            continue
        if _has(p,positive):tags["rhythm" if any(x in value for x in ("drums","808","kick")) else "instruments"].append(value)
    # A Russian vocalist needs this guidance, but not the original 160-char paragraph.
    if prepared.get("vocal_language")=="ru" and not prepared.get("instrumental"):
        if not any("Russian" in x for x in tags["voices"]):
            tags["voices"].append("natural Russian vowels, word stress and legato")
    bpm=re.search(r"\b(\d{2,3})\s*BPM\b",style,re.I)
    tonality=re.search(r"\b([A-G](?:#|b)?)\s*(major|minor)\b",style,re.I)
    if bpm:tags["other"].append(bpm[1]+" BPM")
    if tonality:tags["other"].append(tonality[1].upper()+" "+tonality[2].lower())
    if _has(r"piano.{0,25}(?:resolved|resolution|ending|outro)|(?:resolved|resolution|musical).{0,30}(?:piano|ending)|завершен|финал.*(?:пианино|фортепиано)",combined):
        tags["other"].append("resolved piano outro and natural decay")
    negatives=plan.get("excluded",[])
    if negatives:tags["other"].extend("no "+x for x in negatives)
    # Additional explicit instruments detected in the established v26 mapping.
    for inst in plan.get("instruments",[]):
        if inst=="808 bass" and any("808" in desc for desc in tags["rhythm"]):continue
        if not any(inst in desc for desc in tags["instruments"]+tags["rhythm"]):
            tags["instruments"].append(inst)
    distinct=[];seen=set()
    for group in ("genres","other","mood","voices","instruments","rhythm","mix"):
        for item in tags[group]:
            key=item.lower()
            if key not in seen:seen.add(key);distinct.append((group,item))
    return distinct,tags

def compile_brief(style,prepared):
    text=str(style or "").strip()
    old=previous(text,prepared)
    details,tags=summarize(text,prepared,old)
    # Words 'SFX:' form a post-production plan, not a model-generated musical
    # instrument. Save them fully but spend no part of 512 model chars on them.
    # Keep a comma-separated SFX block out of musical caption, not just its first item.
    sfx_blocks=re.findall(r"\b(?:SFX|FX)\s*:\s*([^\n.]+)",text,re.I)
    audio_brief=re.sub(r"\b(?:SFX|FX)\s*:\s*[^\n.]+", "",text,flags=re.I)
    terms=_parts(audio_brief)
    known_tokens=set(re.findall(r"[a-zа-яё0-9]+"," ".join(i for _,i in details).lower()))
    fallback=[]
    for part in terms:
        tokens=set(re.findall(r"[a-zа-яё0-9]+",part.lower()))
        if not tokens:continue
        if _has(r"^\s*(?:sfx|fx)\s*:",part):continue
        if _has(r"chant|ad.?libs",part) and any(_has(r"chant|adlibs",v) for _,v in details):continue
        fraction=len(tokens & known_tokens)/max(len(tokens),1)
        # Preserve niche instructions not covered by the precompiled categories.
        if fraction<.28 and len(part)<=125 and len(part)>=4:
            fallback.append(part)
    for part in fallback:
        details.append(("unclassified",part))
    result=[];kept=[];omitted=[];used=set()
    # Prefer all recognizable separate instrumental roles before less important adjectives.
    order={"genres":0,"other":1,"voices":2,"instruments":3,"rhythm":4,"mood":5,"mix":6,"unclassified":7}
    for group,chunk in sorted(details,key=lambda x:order.get(x[0],8)):
        key=chunk.lower().strip(" .")
        if key in used:continue
        used.add(key)
        if len("; ".join(result+[chunk]))<=MAX:
            result.append(chunk);kept.append({"category":group,"text":chunk})
        else:omitted.append({"category":group,"text":chunk})
    if not result:result=[text[:MAX].rsplit(" ",1)[0]] if text else ["instrumental soundtrack"]
    caption="; ".join(result)
    plan=old["style_plan"]
    plan["prompt_compiler"]="loss_aware_style30"
    plan["complete_style_source"]=text
    plan["structured_style_requirements"]=tags
    plan["unpacked_fragments"]=terms
    plan["model_caption"]=caption
    plan["kept_directions"]=kept
    plan["not_sent_to_model"]=omitted
    plan["omitted"]=[p["text"] for p in omitted]
    plan["caption_limit"]=MAX
    plan["caption_used"]=len(caption)
    plan["caption_full_source_length"]=len(text)
    plan["sound_effects_in_style"]=[s.strip() for block in sfx_blocks for s in block.split(",") if s.strip()]
    plan["model_is_guaranteed_to_follow"]=False
    old["caption"]=caption
    old["style_plan"]=plan
    old["warnings"]=[x for x in old["warnings"] if not x.startswith("Не вместилось в 512")]
    if omitted:
        old["warnings"].append("Промпт сохранён целиком, но в 512 символов ACE-Step не переданы: "+", ".join(x["text"] for x in omitted[:12])+". Эти пункты видны в плане; выполнение моделью не гарантировано.")
    old["warnings"].append("Полный музыкальный план сохранён; в модель отправлен компактный промпт "+str(len(caption))+"/"+str(MAX)+" символов. SFX вставляются отдельно.")
    return old
