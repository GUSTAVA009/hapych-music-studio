"""Automatic offline cover artwork for Music Studio.

This is algorithmic illustration based on the song's saved title/style. No
external API, network or GPU call. Existing MP3s and voice files are untouched.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

_SIZE = 640
_LOCK = threading.RLock()
_FOLDER = "Обложки треков"

_PALETTES = [
    ((10, 23, 46), (73, 65, 93), (245, 162, 103), (255, 205, 126)),
    ((12, 19, 39), (33, 58, 82), (112, 198, 204), (237, 180, 131)),
    ((13, 18, 31), (76, 37, 69), (221, 119, 141), (255, 204, 140)),
    ((15, 30, 34), (34, 75, 71), (170, 181, 107), (255, 194, 117)),
    ((10, 17, 39), (35, 43, 83), (109, 134, 225), (224, 154, 201)),
    ((29, 20, 37), (96, 44, 54), (255, 148, 100), (255, 217, 164)),
    ((10, 29, 39), (34, 88, 102), (100, 197, 182), (243, 199, 130)),
]

def _color_mix(a, b, f):
    return tuple(int(a[i] * (1.0-f) + b[i] * f) for i in range(3))


def _genre_theme(text: str, seed: int) -> str:
    v = text.casefold()
    if any(w in v for w in ("море", "моря", "берег", "прибой", "остров", "пляж", "курорт", "seaside", "summer", "tropical", "ocean", "beach")):
        return "coast"
    if any(w in v for w in ("rap", "trap", "808", "drill", "хип", "рэп", "rnb", "street", "club", "ночной", "сочи", "синт", "dance", "bass", "hip-hop", "hip hop")):
        return "neon-city"
    if any(w in v for w in ("космос", "звезд", "space", "ambient", "dream", "astral", "sci-fi", "galactic")):
        return "astral"
    if any(w in v for w in ("рок", "rock", "metal", "гитарный рок", "горы", "ветер", "folk", "инди")):
        return "highlands"
    if any(w in v for w in ("love", "любов", "роман", "нежный", "acoustic", "баллад", "soft")):
        return "coast" if seed % 2 else "highlands"
    return ("neon-city", "coast", "highlands", "astral")[seed % 4]


def _font(size: int, bold=False):
    candidates = [
        ("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        ("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        "DejaVuSans.ttf",
    ]
    for file in candidates:
        try:
            return ImageFont.truetype(file, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _background(rng: np.random.Generator, palette, focus_x: int, focus_y: int) -> Image.Image:
    size = _SIZE
    a, b, c, d = palette
    yy, xx = np.mgrid[:size, :size].astype("float32")
    t = (yy / (size-1))[..., None]
    top = np.array(a, dtype="float32")
    bottom = np.array(b, dtype="float32")
    image = top[None, None, :] * (1-t) + bottom[None, None, :] * t
    fx, fy = focus_x, focus_y
    radius = ((xx - fx)**2 / (size * .72)**2 + (yy - fy)**2 / (size * .54)**2)
    halo = np.maximum(0, 1 - np.sqrt(radius))
    golden = np.array(c, dtype="float32")
    glow = (halo**2 * .42)[..., None]
    image = image * (1-glow) + golden[None, None, :] * glow
    mist = (.11*np.sin(xx/55 + yy/96) + .08*np.sin(xx/125 - yy/61))[..., None]
    image += mist * np.array(d, dtype="float32")[None,None,:]*.42
    grain = rng.normal(0, 4.0, (size,size,1)).astype("float32")
    image += grain
    vignette = np.clip(((xx-size/2)**2+(yy-size/2)**2) / (size*.80)**2, 0, .8)[...,None]
    image *= (1 - vignette * .24)
    return Image.fromarray(np.uint8(np.clip(image, 0, 255)), "RGB").convert("RGBA")


def _stars(draw, rng, amount=55, color=(245, 219, 199)):
    for _ in range(amount):
        x=int(rng.integers(0,_SIZE))
        y=int(rng.integers(10,390))
        r=float(rng.uniform(.5,1.8))
        alpha=int(rng.integers(55,155))
        draw.ellipse((x-r,y-r,x+r,y+r), fill=color+(alpha,))


def _coast(layer, rng, p, lightx, lighty):
    n=_SIZE
    draw=ImageDraw.Draw(layer,"RGBA")
    ac=p[2];soft=p[3]
    _stars(draw,rng,32)
    # Distant light and atmospheric sun/moon disk.
    for r,alpha in [(109,11),(79,17),(56,35),(38,40)]:
        draw.ellipse((lightx-r,lighty-r,lightx+r,lighty+r), fill=soft+(alpha,))
    r=45
    draw.ellipse((lightx-r,lighty-r,lightx+r,lighty+r), fill=soft+(201,))
    horizon=int(rng.integers(346,416))
    draw.rectangle((0,horizon,n,n),fill=(12,38,55,205))
    for i in range(260):
        y=int(rng.integers(horizon+3,n))
        spread=((y-horizon)/(n-horizon))**1.3
        x=int(rng.normal(lightx,70+230*spread))
        width=int(rng.integers(5,22)+spread*46)
        alpha=int(rng.integers(25,110)* (1 - spread*.24))
        draw.line((x-width//2,y,x+width//2,y),fill=soft+(alpha,),width=max(1,int(1+spread)))
    for j in range(7):
        y=horizon+14+j*33+int(rng.integers(-7,8))
        draw.arc((-160,y-38,n+120,y+36),0,180,fill=(130,204,199,53),width=2)
    if rng.random()<.75:
        # Right-hand foreground rocky shore and a sailboat silhouette
        draw.polygon([(n*.75,n),(n*.82,n*.79),(n*.95,n*.71),(n,n*.75),(n,n)],fill=(8,27,37,208))
        boatx=int(rng.integers(n//5,n//2));boaty=horizon+55
        draw.line((boatx,boaty-56,boatx,boaty),fill=(14,28,38,245),width=3)
        draw.polygon([(boatx+2,boaty-54),(boatx+3,boaty-5),(boatx+34,boaty-6)],fill=(236,210,182,110))
        draw.arc((boatx-24,boaty-5,boatx+26,boaty+12),0,180,fill=(11,26,31,225),width=6)


def _city(layer, rng, p, lightx, lighty):
    n=_SIZE
    draw=ImageDraw.Draw(layer,"RGBA")
    _stars(draw,rng,26,p[3])
    horizon=int(rng.integers(325,395))
    draw.polygon([(0,n),(0,horizon),(n,horizon+int(rng.integers(10,60))),(n,n)],fill=(9,19,33,216))
    x=-8
    buildings=[]
    while x<n:
        width=int(rng.integers(28,72));height=int(rng.integers(72,216))
        y=horizon-height+int(rng.integers(-22,23))
        draw.rectangle((x,y,x+width,horizon+12),fill=(8,19,33,244))
        buildings.append((x,y,width))
        if rng.random()<.35:draw.line((x+width//2,y,x+width//2,y-16),fill=p[2]+(115,),width=2)
        x+=width+int(rng.integers(0,13))
    for x,y,width in buildings:
        for col in range(max(1,(width-5)//12)):
            for row in range(1,17):
                xx=x+6+col*12;yy=y+8+row*13
                if yy>horizon-8:break
                if rng.random()<.38:
                    color=p[3] if rng.random()<.45 else (111,205,213)
                    draw.rectangle((xx,yy,xx+3,yy+5),fill=color+(int(rng.integers(60,170)),))
    draw.polygon([(0,n),(n,n),(int(n*.61),horizon+20),(int(n*.4),horizon+20)],fill=(19,28,44,229))
    for i in range(13):
        yy=horizon+20+i*(n-horizon)//15
        wid=int(4+(yy-horizon)*.16)
        xx=int(n*.5 + np.sin(i*.35)*25)
        draw.line((xx-wid,yy,xx+wid,yy),fill=p[3]+(int(rng.integers(60,130)),),width=2)
    for _ in range(21):
        x=int(rng.integers(0,n));y=int(rng.integers(horizon,n))
        dest=int(rng.integers(8,55))
        draw.line((x,y,x+dest,y),fill=p[2]+(int(rng.integers(40,135)),),width=int(rng.integers(1,3)))
    draw.line((0,horizon+7,n,horizon+23),fill=p[2]+(75,),width=2)


def _highlands(layer, rng, p, lightx, lighty):
    n=_SIZE
    draw=ImageDraw.Draw(layer,"RGBA")
    _stars(draw,rng,58,p[3])
    draw.ellipse((lightx-55,lighty-55,lightx+55,lighty+55),fill=p[3]+(155,))
    layers=[(320,(39,65,79,195)),(403,(18,45,60,230)),(505,(10,28,43,250))]
    for start,col in layers:
        pts=[(0,n),(0,start+int(rng.integers(-40,15)))]
        for x in range(45,n+75,45):
            pts.append((x,start+int(rng.integers(-115,55))))
        pts.append((n,n))
        draw.polygon(pts,fill=col)
    for _ in range(32):
        x=int(rng.integers(0,n));y=int(rng.integers(445,580))
        h=int(rng.integers(28,110))
        draw.line((x,y,x,y-h),fill=(7,25,31,200),width=3)
        for s in range(4):
            width=(4-s)*6+int(rng.integers(3,9))
            yy=y-h+9+s*11
            draw.polygon([(x-width,yy+9),(x,yy-18),(x+width,yy+9)],fill=(7,27,32,190))
    for _ in range(8):
        y=int(rng.integers(520,650))
        draw.line((0,y,n,y+int(rng.integers(-11,12))),fill=p[3]+(32,),width=2)


def _astral(layer, rng, p, lightx, lighty):
    n=_SIZE
    draw=ImageDraw.Draw(layer,"RGBA")
    _stars(draw,rng,130,p[3])
    cx=int(rng.integers(n//3,n*2//3));cy=int(rng.integers(250,385))
    for i in range(18,1,-1):
        rr=26*i
        draw.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),outline=p[2]+(max(10,int(110/(i**.60))),),width=2)
    for _ in range(15):
        ang=float(rng.uniform(-math.pi,math.pi));rr=float(rng.integers(150,320))
        x=cx+math.cos(ang)*rr;y=cy+math.sin(ang)*rr
        draw.line((cx,cy,x,y),fill=p[3]+(int(rng.integers(25,65)),),width=int(rng.integers(1,4)))
    draw.ellipse((cx-76,cy-76,cx+76,cy+76),fill=(16,24,47,240))
    draw.ellipse((cx-58,cy-58,cx+58,cy+58),fill=p[2]+(195,))
    draw.ellipse((cx-38,cy-38,cx+38,cy+38),fill=p[3]+(165,))
    draw.polygon([(0,n),(0,535),(n//2,489),(n,535),(n,n)],fill=(9,21,38,150))


def _fit_title(draw, text, font_path=None):
    raw=re.sub(r"\s+"," ",str(text or "МОЯ МУЗЫКА")).strip()
    if len(raw)>90:raw=raw[:87].rstrip()+"…"
    max_width=_SIZE-100
    for size in (39,36,33,30,27,24):
        ft=_font(size,True)
        words=raw.split()
        lines=[]
        for word in words:
            trial=(lines[-1]+" "+word) if lines else word
            if lines and draw.textbbox((0,0),trial,font=ft)[2] <= max_width:
                lines[-1]=trial
            else:
                lines.append(word)
        if len(lines)<=3 and all(draw.textbbox((0,0),line,font=ft)[2]<=max_width for line in lines):
            return lines,ft
    return [raw[:28]+"…" if len(raw)>28 else raw],_font(24,True)


def _illustrate(filename: str, title: str, style: str, lyrics: str="") -> Image.Image:
    identifier=int.from_bytes(hashlib.sha256(filename.encode("utf-8")).digest()[:8],"big")
    rng=np.random.default_rng(identifier)
    palette=_PALETTES[(identifier//17)%len(_PALETTES)]
    match=_genre_theme(title+" "+style+" "+lyrics[:180],identifier)
    lx=int(rng.integers(170,480));ly=int(rng.integers(170,285))
    canvas=_background(rng,palette,lx,ly)
    atmosphere=Image.new("RGBA",(_SIZE,_SIZE))
    render={"coast":_coast,"neon-city":_city,"highlands":_highlands,"astral":_astral}[match]
    render(atmosphere,rng,palette,lx,ly)
    # Keep the atmosphere clear: illustrations, not gradients + musical note icons.
    canvas=Image.alpha_composite(canvas,atmosphere)
    draw=ImageDraw.Draw(canvas,"RGBA")
    # Readable but subtle typography treatment at bottom.
    for y in range(410,_SIZE):
        t=(y-410)/(_SIZE-410)
        alpha=int(18+217*(t*t))
        draw.line((0,y,_SIZE,y),fill=(4,10,20,alpha),width=1)
    draw.line((43,502,166,502),fill=palette[3]+(190,),width=3)
    draw.text((44,35),"M U S I C   S T U D I O",font=_font(17,True),fill=(247,246,241,205))
    lines,font=_fit_title(draw,title)
    line_height=draw.textbbox((0,0),"AgЙё",font=font)[3]+12
    start=_SIZE-60-line_height*len(lines)
    for i,line in enumerate(lines):
        draw.text((44,start+i*line_height),line,font=font,fill=(250,251,253,246),stroke_width=1,stroke_fill=(10,20,29,70))
    # No fake artist credit; indicate genre-based illustration.
    small={"coast":"COASTAL • SOUND","neon-city":"NIGHT • SOUND","highlands":"NATURE • SOUND","astral":"ATMOSPHERIC • SOUND"}[match]
    draw.text((44,_SIZE-37),small,font=_font(14),fill=palette[3]+(185,))
    canvas=canvas.convert("RGB")
    return canvas.resize((512,512),Image.Resampling.LANCZOS)


def cover_path(track: Path) -> Path:
    digest=hashlib.sha256(("art35-v2:"+track.name).encode("utf-8")).hexdigest()[:28]
    return track.parent.parent / _FOLDER / (digest+".webp")


def ensure_cover(track: Path) -> Path:
    track=Path(track)
    if not track.is_file() or track.suffix.lower()!=".mp3":
        raise ValueError("No MP3 exists for cover artwork")
    dest=cover_path(track)
    if dest.is_file() and dest.stat().st_size>1300:
        return dest
    with _LOCK:
        if dest.is_file() and dest.stat().st_size>1300:
            return dest
        metadata=track.with_suffix(".track.json")
        saved={}
        if metadata.exists():
            try:saved=json.loads(metadata.read_text(encoding="utf-8"))
            except (OSError,ValueError):pass
        title=str(saved.get("title") or track.stem).strip()[:150]
        style=str(saved.get("style_original") or saved.get("caption_sent") or "")[:3000]
        lyrics=str(saved.get("lyrics_original") or "")[:1500]
        dest.parent.mkdir(parents=True,exist_ok=True)
        poster=_illustrate(track.name,title,style,lyrics)
        temp=dest.with_suffix(".part.webp")
        try:
            poster.save(temp,format="WEBP",quality=86,method=5)
            temp.replace(dest)
        finally:
            temp.unlink(missing_ok=True)
    return dest


if __name__=="__main__":
    import argparse,time,sys
    parser=argparse.ArgumentParser()
    parser.add_argument("--folder",required=True)
    parser.add_argument("--limit",type=int,default=0)
    args=parser.parse_args()
    tracks=Path(args.folder)
    files=list(tracks.glob("*.mp3"))
    files.sort(key=lambda f:f.stat().st_mtime,reverse=True)
    if args.limit:files=files[:args.limit]
    start=time.perf_counter()
    count=0;errors=[]
    for i,f in enumerate(files,1):
        try:
            dest=ensure_cover(f)
            count+=1
            if i<=5 or i%20==0 or i==len(files):
                print("COVER_PROGRESS",i,len(files),dest.stat().st_size,f.name[:50],flush=True)
        except Exception as exc:
            errors.append((f.name,str(exc)))
    print("COVER_REPORT",count,len(files),"elapsed",round(time.perf_counter()-start,2),"errors",errors[:4],flush=True)
    sys.exit(1 if errors else 0)
