"""Retrieve original generation instructions for a single, validated local track.
Never substitute currently edited inputs for historical metadata.
"""
from pathlib import Path
import json,re

def _json(path):
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,UnicodeError,ValueError):
        pass
    return {}

def get_details(filename,tracks,originals):
    path=tracks/filename
    if not path.is_file() or path.parent.resolve()!=tracks.resolve():
        raise FileNotFoundError('Трек не найден')
    metadata=_json(path.with_suffix('.track.json'))
    candidates=[]
    m=re.match(r'^(\d{8}_\d{6}_[0-9a-fA-F]{6})_',path.name)
    if m:candidates=list(originals.glob(m[1]+'*.session.json'))
    if not candidates:
        candidates=list(originals.glob('*.session.json'))
    record=None;item={}
    for candidate in candidates:
        session=_json(candidate)
        for found in session.get('files',[]):
            if found.get('name')==path.name:
                record=session;item=found;break
        if record is not None:break
    raw_style=str(metadata.get('style_original') or '')
    raw_lyrics=str(metadata.get('lyrics_original') or '')
    caption=str(metadata.get('caption_sent') or '')
    model_lyrics=str(metadata.get('lyrics_sent') or '')
    plan=metadata.get('style_plan') or {}
    variant=metadata.get('variant') or item.get('variant') or 1
    if record:
        request=record.get('requested') or {}
        defaults=record.get('engine_settings') or {}
        variants=record.get('variant_settings') or []
        current=next((v for v in variants if v.get('variant')==variant),{})
        settings=current.get('settings') or {}
        raw_style=str(request.get('style') or raw_style)
        raw_lyrics=str(request.get('lyrics') or raw_lyrics)
        caption=str(settings.get('Music Caption') or defaults.get('Music Caption') or caption)
        model_lyrics=str(settings.get('Lyrics') or defaults.get('Lyrics') or model_lyrics)
        plan=current.get('prompt_plan') or plan
    title=str(metadata.get('title') or item.get('title') or path.stem)
    # No song/brief guessing from file name: absence must be explicit.
    return {
       'name':path.name, 'title':title,'variant':variant,
       'style_original':raw_style,'model_caption':caption,
       'lyrics_original':raw_lyrics,'lyrics_sent':model_lyrics,
       'style_plan':plan if isinstance(plan,dict) else {},
       'found':bool(raw_style or raw_lyrics or caption or model_lyrics),
       'has_session':record is not None,
       'status':'Данные сохранённой генерации' if record else
           'Данные карточки трека' if metadata.get('style_original') else
           'Для старого файла промпт и текст не сохранились',
    }
