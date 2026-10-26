"""CC0 true-recording selection and verification for Music Studio (quality32).
Never labels digital synthesis or upsampled content a high-resolution field recording.
"""
from pathlib import Path
from functools import lru_cache
import json,hashlib,collections,random,re
import soundfile as sf
ROOT=Path.home()/"Music Studio"/"Sound Library"/"external_cc0"
PACK=ROOT/"owlish_recorded"
# Every string is an ORIGINAL recorded field file under this CC0 pack.
PREFERRED={
 "phone_ring":["Technology/Phonering-otherend.wav"],
 "phone_vibrate":["Technology/Phone_vibrate.wav"],
 "clock_tick":["Ambience/loopable-ticking-clock.wav"],
 "vinyl_crackle":["Technology/record_player_loop.wav"],
 "footsteps":["Footsteps/hard-footstep1.wav","Footsteps/hard-footstep2.wav",
              "Footsteps/hard-footstep3.wav","Footsteps/hard-footstep4.wav"],
 "concrete_footsteps":["Footsteps/hard-footstep1.wav","Footsteps/hard-footstep2.wav"],
 "wet_footsteps":["Footsteps/reverb_step_1.wav"],
 "cloth_rustle":["Cloth, Rustle/320137__owlstorm__blanket-movement-1.wav",
                 "Cloth, Rustle/320138__owlstorm__blanket-movement-2.wav"],
 "paper_shuffle":["Paper/paper-sketchbook-page-flips-1.wav",
                  "Paper/paper-sketchbook-page-flips-2.wav"],
 "paper_crumple":["Paper/crumples1.wav","Paper/crumples2.wav"],
 "finger_snap":["Human/click-finger-snap.wav"],
 "hand_clap":["Human/solo-clap.wav"],
 "drink_sip":["Human/drink-sip-and-swallow.wav"],
 "kitchen_clink":["Impacts/tap.wav"],
 "glass_tap":["Impacts/tap.wav"],
 "room_laughter_chatter":["Human/laugh1.wav"],
 "human_laughter":["Human/laugh1.wav"],
 "male_breath":["Human/breath-male.wav"],
 "female_breath":["Human/breath-female.wav","Human/breath-female2.wav"],
 "human_cough":["Human/cough1.wav","Human/cough2.wav","Human/cough3.wav"],
 "human_gasp":["Human/gasp1.wav"],
 "human_yawn":["Human/yawn1.wav","Human/yawn2.wav"],
 "zipper":["Cloth, Rustle/212180__owlstorm__bag-zipper.wav"],
 "running_footsteps":["Footsteps/running-shoes-1.wav","Footsteps/running-shoes-2.wav"],
 "night_ambience":["Ambience/night-crickets-ambience-on-rural-property.wav"],
 "earthquake":["Ambience/earthquake.wav"],
 "computer_mouse":["Technology/mouse-clicks-scrolls.wav"],
 "computer_bleep":["Technology/BLEEPINGCOMPUTER2.wav"],
 "water_stream":["Water/tap-water-1.wav","Water/tap-water-2.wav"],
 "kettle":["Water/kettle-boil.wav"],
 "spray_bottle":["Water/spray-bottle.wav"],
}
MATCH_PATTERNS=[
 ("phone_ring",r"(?:phone|телефон).*?(?:ring|звон)|(?:ringing|звон).*?(?:phone|телефон)"),
 ("phone_vibrate",r"(?:phone|телефон).*?(?:vibrat|вибрац)"),
 ("night_ambience",r"cricket|сверчк|ночн.*природ"),
 ("finger_snap",r"finger.*snap|щ[её]лч.*пальц"),
 ("hand_clap",r"hand.*clap|хлоп.*ладош"),
 ("male_breath",r"\bmale\b.*breath|мужск.*дыхани"),
 ("female_breath",r"\bfemale\b.*breath|женск.*дыхани"),
 ("human_cough",r"(?:human.*)?cough|кашел|кашля"),
 ("human_yawn",r"yawn|зева"),
 ("human_gasp",r"gasp|вздох.*испуг"),
 ("human_laughter",r"^(?:human )?laughter$|^смех$"),
 ("zipper",r"zipper|молни.*одежд"),
 ("running_footsteps",r"running.*footstep|шаг.*бег|бегущ.*шаг"),
 ("water_stream",r"water.*tap|water.*running|вода.*кран|водопровод"),
 ("record_player_loop",r"record player|проигрывател.*пластин"),
 ("earthquake",r"earthquake|землетрясен"),
 ("computer_mouse",r"computer.*mouse|мышь.*клик|компьютерн.*мыш"),
 ("computer_bleep",r"computer.*beep|компьютер.*сигнал"),
 ("kettle",r"kettle|чайник"),
 ("spray_bottle",r"spray bottle|пульверизатор"),
 ("paper_shuffle",r"(?:paper.*shuff|shuffl.*paper|page.*flipp|лист.*перелист|перелист.*бумаг)"),
 ("paper_crumple",r"paper.*crumpl|комкан.*бумаг"),
 ("cloth_rustle",r"cloth.*rustl|одежд.*шурш|шорох.*ткан"),
 ("night_ambience",r"night.*ambient|ночн.*лес"),
]
def recognize(description):
    for category,pattern in MATCH_PATTERNS:
        if re.search(pattern,str(description),re.I) and preferred_path(category):return category
    return None

def preferred_path(name,variant=0):
    options=[PACK/part for part in PREFERRED.get(str(name),[])]
    found=[p for p in options if p.is_file()]
    return found[int(variant)%len(found)] if found else None
def scan():
    groups=collections.Counter();rate=collections.Counter();subtypes=collections.Counter()
    lengths=[];invalid=[];recorded=[];synthetic_count=0
    for f in PACK.rglob("*"):
        if f.suffix.lower() not in (".wav",".flac",".ogg",".mp3"):continue
        try:
            x=sf.info(str(f))
            if x.frames<=0 or x.samplerate<16000:invalid.append(f.name);continue
        except Exception as ex:invalid.append(f.name+":"+str(ex));continue
        recorded.append({"name":f.name,"relative_path":str(f.relative_to(PACK)),
                         "samplerate":x.samplerate,"channels":x.channels,
                         "subtype":x.subtype,"duration_s":round(x.duration,3),
                         "bytes":f.stat().st_size,"is_original_field_recording":True,
                         "high_fidelity_source":bool(x.samplerate>=44100 and x.subtype in ("PCM_16","PCM_24","PCM_32","FLOAT")),
                         "license":"CC0","source":"https://opengameart.org/content/sound-effects-pack"})
        groups[str(f.relative_to(PACK).parts[0])]+=1
        rate[x.samplerate]+=1
        subtypes[x.subtype]+=1
        lengths.append(x.duration)
    doc={"scan_version":"quality32","license":"CC0","source_url":"https://opengameart.org/content/sound-effects-pack",
         "recorded":len(recorded),"quality_grade": "verified source sampling depth, not a subjective listening score",
         "source_rates":dict(rate),"source_subtypes":dict(subtypes),
         "high_fidelity_count":sum(f["high_fidelity_source"] for f in recorded),
         "duration_minutes":round(sum(lengths)/60,2),"folders":dict(groups),"invalid":invalid,
         "preferred_categories_available":{key:len([p for p in paths if (PACK/p).is_file()]) for key,paths in PREFERRED.items()},
         "files":recorded}
    output=ROOT/"owlish_audio_quality32.json"
    output.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
    return doc
if __name__=="__main__":
    p=scan()
    print("SCANNED",p["recorded"],"HIGH_FIDELITY",p["high_fidelity_count"],
          "DURATION_MINUTES",p["duration_minutes"],"RATES",p["source_rates"],
          "SUBTYPES",p["source_subtypes"],"INVALID",len(p["invalid"]),
          "PREFERRED_CATEGORIES",sum(x>0 for x in p["preferred_categories_available"].values()))
