"""Searchable SFX catalog v30; only locally installed CC0 packs.
Exact sample IDs or curated RU/EN synonyms; no misleading fuzzy substitution.
"""
from pathlib import Path
from functools import lru_cache
from hashlib import sha256
from sound_quality32 import PREFERRED, preferred_path, recognize as recognize_recorded
import re
ROOT=Path.home()/"Music Studio"
BANK=ROOT/"Sound Library"
EXT=BANK/"external_cc0"
EXTENSIONS={".wav",".mp3",".ogg",".flac",".aiff"}
GROUPS=["owlish_recorded","metal27","breaks75","clickety87","urban100","woodmetal100","household202","random58","scifi70",
        "casino","rpg","interface","retro512","realworld"]
# Alias, explicit source pack, token in filename. A grouped source has
# multiple alternate recordings which can rotate between takes.
CHOICES={
 "metal_collision_hifi":("metal27","dull_metal_collision_"),
 "metal_grit_hifi":("metal27","metal_grit_"),
 "metal_clangs_hifi":("metal27","rapid_clangs_"),
 "metal_wobble_hifi":("metal27","wobble_"),
 "glass_break_hifi":("breaks75","bfh1_glass_breaking_"),
 "glass_fall_hifi":("breaks75","bfh1_glass_falling_"),
 "metal_fall_hifi":("breaks75","bfh1_metal_falling_"),
 "metal_hit_hifi":("breaks75","bfh1_metal_hit_"),
 "fall_impact_hifi":("breaks75","bfh1_falling_"),
 "heavy_hit_hifi":("breaks75","bfh1_hit_"),
 "breaking_hifi":("breaks75","bfh1_breaking_"),
 "clicks_hifi":("clickety87","click"),
 "thunder":("urban100","sfx100v2_thunder"),
 "city_traffic":("urban100","sfx100v2_loop_highway"),
 "construction_site":("urban100","sfx100v2_loop_construction"),
 "factory_machinery":("urban100","sfx100v2_loop_machine"),
 "running_water":("urban100","sfx100v2_loop_water"),
 "city_ambience":("urban100","sfx100v2_loop_ambient"),
 "wind_gust":("urban100","sfx100v2_air"),
 "wet_footsteps":("urban100","sfx100v2_footstep_wet"),
 "wood_footsteps":("urban100","sfx100v2_footstep_wood"),
 "concrete_footsteps":("urban100","sfx100v2_footstep_0"),
 "glass_break":("urban100","sfx100v2_glass"),
 "metal_impact":("woodmetal100","metal_hit"),
 "metal_slam":("woodmetal100","metal_slam"),
 "metal_sheet":("woodmetal100","metal_sheet"),
 "wood_crack":("woodmetal100","wood_cracking"),
 "wood_break":("woodmetal100","wood_breaking"),
 "wood_slam":("woodmetal100","wood_slam"),
 "creaking_wood":("woodmetal100","wood_squeak"),
 "door_lock":("woodmetal100","lock_open"),
 "door_open":("woodmetal100","door_open"),
 "key_jangle":("woodmetal100","keys"),
 "hammer":("woodmetal100","hammer"),
 "tools_rattle":("woodmetal100","tools"),
 "light_switch":("urban100","sfx100v2_switch"),
 "stone_drop":("urban100","sfx100v2_stones"),
 "camera_shutter":("household202","camera_"),
 "cloth_rustle":("household202","cloth_"),
 "drink_sip":("household202","drink_"),
 "paper_shuffle":("household202","stationery_"),
 "phone_handling":("household202","phone_"),
 "money_handling":("household202","money_"),
 "kitchen_clink":("household202","kitchen_"),
 "cigarette_lighter":("random58","cigarette_lighter"),
 "card_riffle":("random58","cards_riffle"),
 "knife_scrape":("random58","knife_"),
 "glass_tap":("random58","spoon_on_glass"),
 "spoon_cup":("random58","spoon_on_cup"),
 "finger_snap":("random58","finger_click"),
 "hand_clap":("random58","hand_clap"),
 "paper_crumple":("random58","paper_crunch"),
 "metal_chain":("random58","small_chain_rattle"),
 "scissors":("random58","scissors_snip"),
 "electronic_glitch":("interface","glitch_"),
 "digital_click":("interface","click_"),
 "casino_chips":("casino","chips-handle"),
 "dice_roll":("casino","dice-throw"),
 "sci_fi_laser":("scifi70","laserSmall"),
 "sci_fi_engine":("scifi70","spaceEngine"),
 "sci_fi_explosion":("scifi70","explosionCrunch"),
 "sci_fi_door":("scifi70","doorOpen"),
 "sci_fi_computer":("scifi70","computerNoise"),
 "sci_fi_shield":("scifi70","forceField"),
 "sci_fi_thruster":("scifi70","thrusterFire"),
 "radio_noise":("realworld","ScatterNoise1"),
 "room_laughter_chatter":("realworld","group_giggling"),
 "crowd_shouting":("realworld","crowd_shouting"),
 "alarm_beep":("realworld","alarm"),
 "storm_siren":("realworld","storm_3_siren"),
}
# Prefer specific before general; avoid mapping a siren in storm to police.
ALIASES=[
 ("metal_collision_hifi",r"heavy.*metal.*collision|dull.*metal.*(?:hit|impact|collision)|глух.*удар.*металл"),
 ("metal_grit_hifi",r"metal.*grit|металлическ.*скрежет"),
 ("metal_clangs_hifi",r"rapid.*clang|быстры.*лязг"),
 ("metal_wobble_hifi",r"wobbl.*metal|вибрац.*металл"),
 ("glass_break_hifi",r"(?:glass.*(?:break|shatter|smash)|разбит.*стекл|стекло.*разбива)"),
 ("glass_fall_hifi",r"glass.*fall|падени.*стекл"),
 ("metal_fall_hifi",r"metal.*fall|падени.*металл"),
 ("metal_hit_hifi",r"metal.*hit|удар.*металл"),
 ("fall_impact_hifi",r"fall.*impact|падени.*предмет"),
 ("breaking_hifi",r"breaking.*object|разлом.*предмет"),
 ("clicks_hifi",r"clickety|multi.*clicks|серия.*щелч"),
 ("room_laughter_chatter",r"(?=.*(?:laugh|giggl|смех|смешк))(?=.*(?:chatter|talk|room|разговор|болтовн))|приглушенн.*голоса.*смех"),
 ("crowd_shouting",r"crowd.*(?:shout|yell)|толпа.*(?:крич|орёт)|крики толпы"),
 ("thunder",r"thunder|гром|раскат.*гром|гроза"),
 ("city_traffic",r"city.*(?:traffic|highway|road)|highway|traffic.*city|городск.*трафик|шум.*дорог|магистрал|автомобильный поток"),
 ("construction_site",r"construction.*(?:site|noise)|стройка|строительн.*площадк"),
 ("factory_machinery",r"factory|industrial.*machine|завод.*оборудован|станок|промышленный шум"),
 ("running_water",r"running water|river flow|water stream|течени.*вод|ручей|река.*шум"),
 ("city_ambience",r"city.*ambien|urban.*ambien|городск.*атмосфер|город.*фон"),
 ("wind_gust",r"wind gust|breeze|порыв.*ветр|шум.*ветра"),
 ("wet_footsteps",r"wet.*footstep|footstep.*rain|шаг.*луж|мокр.*шаг|шаг.*дожд"),
 ("wood_footsteps",r"wood.*footstep|footstep.*wood|шаг.*дерев"),
 ("concrete_footsteps",r"concrete.*footstep|footstep.*concrete|шаг.*асфальт|шаг.*бетон"),
 ("glass_break",r"glass.*(?:break|smash|shatter)|разбит.*стекл|звук.*разбит.*бутылк"),
 ("metal_impact",r"metal.*(?:impact|hit|bang)|удар.*металл|металлическ.*удар"),
 ("metal_slam",r"metal.*(?:slam|close)|хлоп.*железн|грохот.*металл"),
 ("metal_sheet",r"metal.*sheet|лист.*металл|жестянк.*грохот"),
 ("wood_crack",r"wood.*crack|треск.*дерев"),
 ("wood_break",r"wood.*break|ломан.*дерев|ломается.*доска"),
 ("wood_slam",r"wood.*slam|хлоп.*дерев"),
 ("creaking_wood",r"creak.*wood|скрип.*дерев"),
 ("door_lock",r"door.*lock|lock.*door|ключ.*замок|закрыт.*замок|щелч.*замк"),
 ("door_open",r"door.*open|opening.*door|дверь.*открывает|открыва.*двер"),
 ("key_jangle",r"key.*jangl|keys.*rattl|звякан.*ключ|звен.*ключ"),
 ("hammer",r"hammer|молоток.*удар|удары.*молотк"),
 ("tools_rattle",r"tools.*rattl|инструмент.*звен|инструмент.*грем"),
 ("light_switch",r"light.*switch|выключател|переключател.*свет"),
 ("stone_drop",r"stone.*(?:fall|drop|hit)|пада.*камень|падени.*камн"),
 ("camera_shutter",r"camera.*(?:shutter|click|shot)|затвор.*камер|щелч.*фотоаппарат"),
 ("cloth_rustle",r"cloth.*rustl|шорох.*ткан|шуршан.*одежд"),
 ("drink_sip",r"drink.*(?:sip|swallow)|глоток.*воды|пить.*воду"),
 ("paper_shuffle",r"paper.*(?:shuffle|rustl|slide)|шурш.*бумаг"),
 ("phone_handling",r"phone.*(?:handling|pickup|place)|клад.*телефон|бер.*телефон"),
 ("money_handling",r"money.*(?:count|handling)|пересчет.*денег|купюр.*шурш"),
 ("kitchen_clink",r"kitchen.*clink|посуд.*стук|кухонн.*звон"),
 ("cigarette_lighter",r"cigarette.*lighter|зажигалк"),
 ("card_riffle",r"card.*riffle|riffle.*shuffle|тасовани.*карт"),
 ("knife_scrape",r"knife.*scrap|нож.*скреж|нож.*царапа"),
 ("glass_tap",r"spoon.*glass|ложк.*стакан|звяк.*стакан"),
 ("spoon_cup",r"spoon.*cup|ложк.*чашк"),
 ("finger_snap",r"finger.*snap|щёлч.*пальц|щелч.*пальц"),
 ("hand_clap",r"hand.*clap|хлоп.*ладош|одиночн.*хлоп"),
 ("paper_crumple",r"paper.*crumpl|комкан.*бумаг|мять.*бумаг"),
 ("metal_chain",r"chain.*rattl|цеп.*звен"),
 ("scissors",r"scissor|ножниц"),
 ("electronic_glitch",r"electronic.*glitch|цифров.*помех|глитч"),
 ("digital_click",r"digital.*click|цифров.*щелч"),
 ("casino_chips",r"casino.*chips|фишк.*казино"),
 ("dice_roll",r"dice.*(?:roll|throw|shake)|брос.*кубик|брос.*кост"),
 ("sci_fi_laser",r"laser|лазер"),
 ("sci_fi_engine",r"space.*engine|двигател.*космич|космич.*двигател"),
 ("sci_fi_explosion",r"sci.?fi.*explos|фантастич.*взрыв"),
 ("sci_fi_door",r"sci.?fi.*door|футуристич.*двер"),
 ("sci_fi_computer",r"computer.*noise|компьютер.*помех"),
 ("sci_fi_shield",r"force.?field|силовое.*поле"),
 ("sci_fi_thruster",r"thruster|реактивн.*двигател"),
 ("radio_noise",r"radio.*(?:noise|static)|радио.*(?:шипен|помех)"),
 ("alarm_beep",r"alarm.*(?:beep|warning)|сигнал.*тревог"),
 ("storm_siren",r"storm.*siren|flood.*siren|сирен.*наводнен"),
]
def normalized(text):
    s=re.sub(r"([a-z])([A-Z])",r"\1 \2",str(text))
    return re.sub(r"\s+"," ",re.sub(r"[^a-zа-яё0-9]+"," ",s.lower())).strip()
@lru_cache(maxsize=1)
def index():
    items={};all_files=[]
    for group in GROUPS:
        folder=EXT/group
        if not folder.is_dir():continue
        for p in sorted(folder.rglob("*")):
            if p.suffix.lower() not in EXTENSIONS or not p.is_file():continue
            if p.stem.lower().startswith("preview") or "__MACOSX" in p.parts:continue
            key=normalized(p.stem)
            if len(key)<4:continue
            all_files.append({"id":group+"/"+p.stem,"label":key,"group":group,"path":str(p)})
            items.setdefault(key,[]).append(p)
            items.setdefault(group+" "+key,[]).append(p)
    return items,all_files
@lru_cache(maxsize=256)
def categories():
    allcats=[]
    for name,items in PREFERRED.items():
        n=sum((Path.home()/"Music Studio"/"Sound Library"/"external_cc0"/"owlish_recorded"/p).is_file() for p in items)
        if n:allcats.append({"id":name,"count":n,"example":items[0].split("/")[-1],"group":"owlish_recorded","source_type":"field_recording_cc0"})
    for key,(group,start) in CHOICES.items():
        folder=EXT/group
        pool=sorted(p for p in folder.rglob("*") if p.suffix.lower() in EXTENSIONS and p.stem.lower().startswith(start.lower())) if folder.is_dir() else []
        if pool:allcats.append({"id":key,"count":len(pool),"example":pool[0].name,"group":group})
    return allcats
def match(query):
    raw=str(query or "").strip()
    if not raw:return None
    # The UI inserts canonical category/sample IDs; recognize them directly.
    # Previously only a human-language phrase would match, resulting in 404s.
    if raw in CHOICES and asset(raw) is not None:return raw
    if raw in PREFERRED and preferred_path(raw) is not None:return raw
    if raw.startswith("sample:") and asset(raw) is not None:return raw
    recorded=recognize_recorded(raw)
    if recorded:return recorded
    # Force stable categorization for natural language instructions.
    for key,pattern in ALIASES:
        if re.search(pattern,raw,re.I) and key in CHOICES and any(x["id"]==key for x in categories()):
            return key
    # Literal source-stem references can select all assets in the installed pack.
    name=normalized(raw)
    known=index()[0]
    if name in known:return "sample:"+name
    if name.startswith("sample "):
        name=name[7:]
        if name in known:return "sample:"+name
    return None
def asset(key,variant=0):
    key=str(key)
    field=preferred_path(key,variant)
    if field is not None:return field
    if key.startswith("sample:"):
        pool=index()[0].get(key[7:],[])
    elif key in CHOICES:
        group,prefix=CHOICES[key]
        folder=EXT/group
        pool=sorted((p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS and p.stem.lower().startswith(prefix.lower()))) if folder.is_dir() else []
    else:return None
    return pool[int(variant)%len(pool)] if pool else None
def stats():
    entries=index()[1]
    return {"total_imported_audio":len(entries),"searchable_specific_samples":len({x["label"] for x in entries}),
            "mapped_categories":len(categories()),"categories":categories()}
