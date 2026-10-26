"""Music Studio 35: beat/arrangement-following SFX placement and ambience gain.
Does not rewrite generated musical notes or phonemes. Untimed SFX estimates are
explicitly labeled; user timestamps always override automatic placement.
"""
import re,math
import numpy as np
from scipy.ndimage import gaussian_filter1d

def bpm_from(prepared):
    for name in ("tempo_bpm","bpm"):
        try:
            value=float(prepared.get(name,0))
            if 30<=value<=300:return value
        except (ValueError,TypeError):pass
    text=str(prepared.get("raw_style") or prepared.get("style") or prepared.get("caption") or "")
    m=re.search(r"\b(\d{2,3})\s*BPM\b",text,re.I)
    if m and 30<=int(m.group(1))<=300:return int(m.group(1))
    return None

def arrange_event(event,prepared,total_seconds):
    """Pull an untimed introductory atmosphere onto an arrangement's bar grid."""
    event=dict(event)
    bpm=bpm_from(prepared)
    name=str(event.get("effect") or "")
    section=str(event.get("section") or "").lower()
    if not bpm or event.get("timing_basis")=="explicit_timestamp":
        return event
    bar=4*60/float(bpm)
    if name in ("rain_asphalt","night_ambience","city_ambience","wind_gust",
                "sea surf","running_water","room_laughter_chatter") and section.startswith("intro"):
        # In a four-bar introduction, ambience is an environment, not a sound hit.
        bars=5 if total_seconds>=30 else 3
        start=0.0
        duration=min(total_seconds,bars*bar)
        event.update(start=start,duration=round(duration,3),
          timing_basis="bpm_bar_grid_intro_environment",
          beat_alignment={"bpm":bpm,"bar_seconds":round(bar,4),"bars":bars,
                          "original_estimate_s":event.get("start"),
                          "release_after_intro_bar":min(4,bars-1)})
        return event
    return event

def music_tied_ambience(chunk,backing,event,sr=48000):
    """Frequency-limited rain/city ambience with bar-stepped musical dynamics.
    Raises/lowers SFX with gradual changes in the music bed rather than assuming
    an SFX text position is the correct musical transition.
    """
    chunk=np.asarray(chunk,dtype=np.float32).copy()
    music=np.asarray(backing,dtype=np.float32)
    n=len(chunk)
    if n<500 or not event.get("beat_alignment"):
        return chunk,{"enabled":False,"reason":"No known BPM bar alignment"}
    bpm=event["beat_alignment"]["bpm"]
    bar=4*60/float(bpm)
    seconds=np.arange(n,dtype=np.float32)/sr
    total=float(n)/sr
    rms=float(np.sqrt(np.mean(chunk.astype("float64")**2)+1e-12))
    if rms<1e-8:return chunk,{"enabled":False,"reason":"Silent sample"}
    # A 10 Hz RMS control track, Gaussian-smoothed across ~0.5 seconds.
    hop=int(sr*.1)
    pad=(-len(music))%hop
    z=np.pad(music,((0,pad),(0,0))).astype(np.float64)
    frame_rms=np.sqrt(np.mean(z.reshape(-1,hop,2)**2,axis=(1,2))+1e-12)
    dbfs=20*np.log10(np.maximum(frame_rms,1e-8))
    smoothed=gaussian_filter1d(dbfs,sigma=4.5,mode="nearest")
    control=np.interp(seconds,np.arange(len(smoothed))*.1,smoothed).astype(np.float32)
    # Rain level approximately 9-15 dB below soft accompaniment; it never
    # follows the main vocal into the foreground when the beat enters.
    music_follow=np.clip(-45+(control+38)*.50,-49,-36)
    # Four phrase-length (bar) stages, joined with 0.6s S-shaped crossfades.
    stage_times=np.array([0,bar,2*bar,3*bar,4*bar,total],dtype=np.float32)
    stage_db=np.array([-4.,-2.5,-1.5,-.5,0.,0.],dtype=np.float32)
    rising=np.interp(seconds,stage_times,stage_db)
    rising=gaussian_filter1d(rising,sigma=max(2.,.25*sr/hop),mode="nearest")
    # Full release across one musical bar AFTER the peak arrangement downbeat.
    release_start=4*bar
    release_end=min(total,5*bar)
    if release_end>release_start+.1:
        prog=np.clip((seconds-release_start)/(release_end-release_start),0,1)
        release=np.cos(prog*np.pi/2)**2
    else:
        release=np.ones(n,dtype=np.float32)
    attack=np.clip(seconds/max(.45,bar*.95),0,1)
    attack=np.sin(attack*np.pi/2)**2
    # Broad, nearly inaudible quarter-note sway (not tremolo or pumping).
    pulse=.982+.018*np.cos((seconds/bar)*np.pi*8)
    target_db=music_follow+rising
    gain=(10**(target_db/20)/rms)*release*attack*pulse
    # Preserve the original sound's dynamics; bounded true peaks for crowding.
    chunk*=gain[:,None].astype(np.float32)
    peak=np.max(np.abs(chunk))
    if peak>.43:chunk*=.43/peak
    def at(sec):
        k=min(n-1,int(sec*sr))
        return round(float(target_db[k]+20*np.log10(max(attack[k]*release[k],1e-9))),2)
    return chunk,{
        "enabled":True,"method":"music_rms_follower_plus_bpm_bar_stages",
        "bpm":bpm,"bar_seconds":round(bar,4),
        "original_estimate_s":event["beat_alignment"].get("original_estimate_s"),
        "intro_release_start_s":round(release_start,3),
        "intro_release_end_s":round(release_end,3),
        "targets_dbfs_at":[{"second":round(t,2),"value":at(t)} for t in
                         (min(total*.15,bar),min(total*.35,bar*2),
                          min(total*.6,bar*3),min(total*.8,bar*4))],
        "actual_peak_dbfs":round(20*np.log10(max(1e-9,float(np.max(np.abs(chunk))))),2),
        "sample_is_recording_not_beat_matched":True,
        "lyrics_alignment_verified":False,
    }
