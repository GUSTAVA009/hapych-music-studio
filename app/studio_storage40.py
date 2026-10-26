from pathlib import Path
import subprocess,os
def storage_paths(root):
    root=Path(root)
    return {key:str(root/folder) for key,folder in {
      "tracks":"Мои треки","covers":"Обложки треков","voices":"Мой голос",
      "trash":"Корзина треков","exports":"Экспорт","originals":"Исходные версии",
      "masters":"Мастер WAV"}.items()}
def open_storage_folder(root,kind):
    dirs=storage_paths(root)
    if kind not in dirs:raise ValueError("Неизвестная папка")
    folder=Path(dirs[kind]);folder.mkdir(parents=True,exist_ok=True)
    if os.name!="nt":raise RuntimeError("Открытие проводника поддерживается только в Windows")
    # Literal fixed directory mapped from a small whitelist, no arbitrary paths.
    subprocess.Popen(["explorer.exe",str(folder)],stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return {"ok":True,"kind":kind,"path":str(folder)}
