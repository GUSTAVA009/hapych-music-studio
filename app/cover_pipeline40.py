"""Local semantic image covers; never competes with an active music job on RTX 4060."""
from pathlib import Path
import json,re,hashlib,threading,subprocess,sys,time,os
from concurrent.futures import ThreadPoolExecutor
from cover_art35 import ensure_cover,cover_path
ROOT=Path(__file__).resolve().parent.parent
MODEL=ROOT/"app"/"models"/"album-sd-turbo"
FOLDER=ROOT/"Обложки треков"
POOL=ThreadPoolExecutor(max_workers=1,thread_name_prefix="cover-art")
LOCK=threading.RLock()
PENDING=set()
def generated_cover_path(track):
    name=hashlib.sha256(("art40:"+track.name).encode("utf-8")).hexdigest()[:28]+".webp"
    return FOLDER/name
def cover_info(track):
    target=generated_cover_path(track)
    with LOCK:running=track.name in PENDING
    if running:return {"status":"generating","source":"semantic_ai","cover_url":"/api/cover/"+track.name}
    if target.is_file() and target.stat().st_size>5000:
        return {"status":"ready","source":"semantic_ai","cover_url":"/api/cover/"+track.name}
    if cover_path(track).exists():return {"status":"fallback","source":"illustration"}
    return {"status":"idle"}
def _scene(track):
    meta=track.with_suffix(".track.json")
    try:m=json.loads(meta.read_text(encoding="utf-8"))
    except Exception:m={}
    title=str(m.get("title") or track.stem)[:200]
    style=str(m.get("style_original") or m.get("caption_sent") or "")[:1400]
    lyrics=str(m.get("lyrics_original") or "")[:2500]
    # Strong concrete scene matching: extract recurring motifs and mood.
    terms=(title+" "+lyrics+" "+style).casefold()
    scene=[]
    tags=[
      (r'bmw|e34|машин|автомоб|гонк|трасс|за рул', "classic sports sedan driving through the city, believable car details"),
      (r'мор[еяю]|пляж|берег|прибой|океан|курорт|sea|beach|summer',"realistic coastal seascape, waves, summer dusk, warm light"),
      (r'ноч|лун|night|midnight',"cinematic night lighting, rich contrast"),
      (r'любов|сердц|поцелу|роман|love',"tender romantic feeling, intimate atmosphere"),
      (r'город|улиц|street|urban|клуб|неон',"modern city scene with cinematic lights"),
      (r'дожд|rain|гроза',"rain reflections, realistic wet surfaces"),
      (r'лес|forest|дерев',"trees and atmospheric woodland"),
      (r'гитар|rock|рок|метал',"dramatic modern rock album art with electric guitar elements"),
      (r'пианино|piano|фортепиано',"piano keys as part of the composition"),
      (r'саксофон|saxophone',"saxophone detail in the scene"),
      (r'космос|звезд|galaxy|space',"stars and cosmic nebula"),
    ]
    for pat,text in tags:
        if re.search(pat,terms):scene.append(text)
    if not scene:scene=["conceptual cinematic illustration expressing "+re.sub(r"[^A-Za-zА-Яа-я0-9 ,.-]","",title)[:100]]
    return "Square premium music album artwork, no writing. "+", ".join(scene[:6])+". "+(
        "Clean art direction, unique deliberate composition, expressive visual storytelling, professional album cover, "
        "detailed textures, physically plausible shapes, strong focal point, visually engaging, no typography, no watermark.")
def _available():
    required=[MODEL/"model_index.json",MODEL/"unet"/"diffusion_pytorch_model.fp16.safetensors",
    MODEL/"vae"/"diffusion_pytorch_model.fp16.safetensors",MODEL/"text_encoder"/"model.fp16.safetensors"]
    return all(x.exists() and x.stat().st_size>500 for x in required)
def _music_busy():
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:7870/api/health",timeout=4) as f: info=json.load(f)
        return info["job"]["status"] in ("preparing","generating","converting") or info.get("training23",{}).get("active") or info.get("training41",{}).get("active")
    except Exception:return True
def _run(track):
    try:
        for _ in range(12):
            if not _music_busy():break
            time.sleep(10)
        else:return
        if not _available():return
        dest=generated_cover_path(track);dest.parent.mkdir(parents=True,exist_ok=True)
        prompt=_scene(track)
        args=[sys.executable,str(Path(__file__).with_name("render_cover40.py")),
              str(MODEL),str(dest),prompt]
        subprocess.run(args,check=True,timeout=190,stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    except Exception as e:
        try:
            (ROOT/"app"/"studio-server.log").open("a",encoding="utf-8").write("COVER40_FAIL "+str(e)[:300]+"\n")
        except Exception:pass
    finally:
        with LOCK:PENDING.discard(track.name)
def queue_cover(track,background=True):
    track=Path(track)
    if not track.is_file() or track.suffix.lower()!=".mp3":return False
    with LOCK:
        if track.name in PENDING or generated_cover_path(track).exists():return False
        if not _available():return False
        PENDING.add(track.name)
    if background:POOL.submit(_run,track)
    else:_run(track)
    return True
def regenerate_cover(track):
    track=Path(track)
    path=generated_cover_path(track)
    if path.exists():path.unlink()
    queued=queue_cover(track,background=True)
    return {"ok":queued,"status":"queued" if queued else "unavailable","model_ready":_available()}
