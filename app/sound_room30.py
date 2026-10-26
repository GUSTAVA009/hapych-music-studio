"""Generate a subdued, stereo room-tone preview from CC0 group voices.
Derived work; only source group vocal recordings are used.
"""
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, resample_poly
from math import gcd
R=Path.home()/"Music Studio"/"Sound Library"
SRC=R/"external_cc0"/"realworld"
TARGET=R/"sfx"/"room_laughter_chatter.wav"
def decode(p):
    a,sr=sf.read(str(p),dtype="float32",always_2d=True)
    if sr!=48000:
        g=gcd(sr,48000);a=resample_poly(a,48000//g,sr//g,axis=0)
    if a.shape[1]==1:a=np.repeat(a,2,axis=1)
    return a[:,:2]
def build():
    if TARGET.is_file():return TARGET
    crowd=SRC/"crowd_shouting.ogg";laugh=SRC/"group_giggling.ogg"
    if not crowd.is_file() or not laugh.is_file():return None
    c=decode(crowd);l=decode(laugh)
    count=max(int(7*48000),len(l))
    def fit(a):
        out=np.zeros((count,2),np.float32)
        for start in range(0,count,len(a)):
            n=min(len(a),count-start)
            out[start:start+n]=a[:n]
        return out
    c=fit(c);l=fit(l)
    sos=butter(3,1700,btype="lowpass",fs=48000,output="sos")
    muffled=sosfiltfilt(sos,c,axis=0)*.12+sosfiltfilt(sos,l,axis=0)*.50
    muffled[:,1]=np.roll(muffled[:,1],2000)
    fade=min(int(.35*48000),count//3)
    muffled[:fade]*=np.linspace(0,1,fade)[:,None]
    muffled[-fade:]*=np.linspace(1,0,fade)[:,None]
    peak=np.max(np.abs(muffled))
    if peak>0:muffled*=.68/max(.68,peak)
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    sf.write(str(TARGET),muffled,48000,subtype="PCM_24")
    import json
    TARGET.with_suffix(".provenance.json").write_text(json.dumps({
      "sources":[str(crowd),str(laugh)],"license":"CC0",
      "credit_urls":["https://opengameart.org/content/group-giggling",
                     "https://opengameart.org/content/crowd-shoutingspeaking-ambience"],
      "description":"Approximation: subdued processed crowd and laughter, not isolated room conversation",
      "processing":"lowpass 1700 Hz, crowd -18 dB below laughter, stereo offset 42 ms",
      "generator":"sound_room30.py"
    },indent=2),encoding="utf-8")
    return TARGET
if __name__=="__main__":
    print("room_chatter",build())
