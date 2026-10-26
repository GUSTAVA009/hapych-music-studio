import sys
sys.path.insert(0, r'C:\Users\YOUR_USERNAME\Music Studio\Voice Engine')
from voice_guard42 import assess_energy

def case(name,ratio,segments,longest):
    total=10000
    drops=int(total*ratio)
    data={'reliable':True,'analysis_seconds':264,'duration_error':0,'active_frames':total,'drop_frames':drops,'drop_segments':[{'start':i,'end':i+(longest if i==0 else .06),'minimum_relative_db':-15} for i in range(segments)]}
    result=assess_energy(data)
    print(name, result['status'],result['accepted'])
    return result['status']
assert case('severe_47_dips',.08384,47,.20)=='rejected'
assert case('minor_2_dips',.02768,2,.08)=='passed_checks'
assert case('moderate_6_dips',.05234,6,.12)=='warning'
print('PASS: all three regression cases')
