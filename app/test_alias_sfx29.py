from studio_sections import compile_sections,prepare_request
from sound_effects29 import planned_effects
raw="""[Intro - Dark Piano]
[SFX Heavy rain on asphalt]
[SFX: Distant police siren]
[Phone Ring SFX]
Новый день, снова район
[Chorus - Male Baritone, Heavy Bass Drop]
Мой голос слышно
[Outro - Vinyl Crackle]
[SFX: Alarm clock ringing]
Опять день сурка
"""
x=compile_sections(raw)
p=planned_effects(x["sections"])
print("EFFECTS",[(e["effect"],e["supported"]) for e in p])
print("MODEL",x["lyrics"])
assert any(e["effect"]=="phone_ring" for e in p)
assert any(e["effect"]=="rain_asphalt" for e in p)
assert any(e["effect"]=="police_siren" for e in p)
assert any(e["effect"]=="alarm_clock" for e in p)
assert "[SFX" not in x["lyrics"]
assert "phone ringing" not in x["lyrics"].lower()
assert all(e["supported"] for e in p)
print("FLEXIBLE SFX SYNTAX OK")
