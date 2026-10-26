from pathlib import Path
import py_compile
R=Path.home()/'Music Studio'/'app'
s=(R/'qa106_harmonic_timbre.py').read_text(encoding='utf8')
s=s.replace('QA106-HarmonicTimbre','QA107-Sweep')
s=s.replace('QA106_','QA107_').replace("'QA106'","'QA107'").replace('QA106_VARIANT','QA107_VARIANT').replace('QA106_GENERATION_COMPLETE','QA107_GENERATION_COMPLETE').replace('qa106_report.json','qa107_report.json')
a="""configs={
 'Harmonic55':(.85,.20,14.0),
 'Harmonic90':(1.4,.35,20.0),
 'Harmonic120':(1.85,.45,23.0),
}"""
b="""configs={
 'Color62':(.96,.24,13.5),
 'Color70':(1.10,.25,14.5),
 'Color78':(1.22,.25,15.0),
 'Color84':(1.28,.30,16.0),
}"""
assert s.count(a)==1
s=s.replace(a,b)
target=R/'qa107_harmonic_sweep.py'
target.write_text(s,encoding='utf8')
py_compile.compile(str(target),doraise=True)
print('QA107_SWEEP_READY',flush=True)
