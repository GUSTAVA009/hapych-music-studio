"""Pre-push safety check for a source-only HAPYCH Music Studio repository.
Never prints possible credentials or user data, only offending filenames.
Does not read .git objects or user audio. Windows / stdlib-only.
"""
from pathlib import Path
import ast,json,re,sys,subprocess
repo=Path(__file__).resolve().parent.parent
# Inspect files that Git will actually publish, not ignored local diagnostic
# logs written by the no-model HTTP regression tests on developers' PCs.
tracked=None
if (repo/'.git').exists():
 p=subprocess.run(['git','-C',str(repo),'ls-files','--cached','-z'],capture_output=True)
 if p.returncode==0:
  tracked={x.decode('utf-8') for x in p.stdout.split(b'\0') if x}
blocked_dir={"__pycache__",".git",".venv","node_modules","checkpoints","Cache",
 "cache","Training Runs","Voice Profiles","Мой голос","Мои треки","Мастер WAV",
 "Исходные версии","Sound Library","Models","models","dataset","datasets","runs",
 "training_dataset","Diagnostics","Exports","Backups"}
allowed_extensions={".py",".pyw",".js",".css",".html",".md",".json",".yml",".yaml",
 ".txt",".toml",".ini",".bat",".cmd",".ps1",".patch",".cs",".csproj",".ico",".gitignore",
 ".gitattributes"}
bad_suffix={".wav",".mp3",".flac",".ogg",".m4a",".safetensors",".ckpt",".pth",
 ".pt",".onnx",".bin",".pem",".key",".p12",".pfx",".env",".zip",".sqlite"}
patterns={
 "private-key":re.compile("-----BEGIN (?:(?:RSA|EC|OPENSSH) )?PRIVATE KEY-----"),
 "github-pat":re.compile("github"+"_"+"pat"+"_[A-Za-z0-9_]{20,}",re.I),
 "github-token":re.compile(r"\bgh"+"[pousr]_[A-Za-z0-9]{30,}",re.I),
 "openai-token":re.compile(r"\bs"+"k-[A-Za-z0-9_-]{30,}",re.I),
 "user-windows-path":re.compile(r"C:\\Users\\alex-",re.I),
 "local-editable":re.compile(r"(?mi)^\s*(-e\s+file:///|[^\s]+@\s+file:///)")
}
errors=[]
count=0
for file in repo.rglob("*"):
 if tracked is not None and file.relative_to(repo).as_posix() not in tracked:continue
 if any(p in blocked_dir for p in file.relative_to(repo).parts):continue
 if not file.is_file():continue
 if file.is_symlink():errors.append((str(file.relative_to(repo)),"symlink"));continue
 rel=file.relative_to(repo)
 if file.suffix.lower() in bad_suffix:
  errors.append((str(rel),"prohibited user/model/binary extension"));continue
 if file.name.startswith(".") and file.name not in (".gitignore",".gitattributes"):
  errors.append((str(rel),"hidden file"));continue
 if file.suffix.lower() not in allowed_extensions and file.name not in (".gitignore",".gitattributes","LICENSE"):
  errors.append((str(rel),"unexpected extension"));continue
 if file.stat().st_size>2_000_000:
  errors.append((str(rel),"oversized source file"));continue
 count+=1
 if file.suffix.lower()==".ico":continue
 try:text=file.read_text(encoding="utf-8-sig")
 except UnicodeDecodeError:
  errors.append((str(rel),"not valid UTF-8"));continue
 for label,pattern in patterns.items():
  if pattern.search(text):
   # Dynamic pattern definitions in this audit script are deliberately excluded
   # from credential matcher checks to avoid false positives.
   if rel==Path("tools/audit_repo.py") and label!="user-windows-path":continue
   errors.append((str(rel),label))
 if file.suffix.lower() in (".py",".pyw"):
  try:ast.parse(text)
  except SyntaxError:errors.append((str(rel),"Python syntax error"))
required=["README.md","LICENSE","Install.cmd","Diagnose.cmd","scripts/Diagnose-Windows.ps1","scripts/Bootstrap-Windows.ps1","docs/INSTALL_WINDOWS.md","docs/MIGRATE_DATA.md",
 "scripts/Install-Windows.ps1","scripts/Start-MusicStudio.ps1",
 "app/studio_server.py","app/ui/index.html",
 "overlays/apexsvc_custom.patch","third_party_versions.json",
 "presets/QA133_ConsonantProtection.json"]
for name in required:
 if not (repo/name).is_file():errors.append((name,"required file missing"))
try:
 m=json.loads((repo/"third_party_versions.json").read_text(encoding="utf-8"))
 assert all(k in m and re.fullmatch("[0-9a-f]{40}",m[k]["commit"])
            for k in ("ace-step","seed-vc","apexsvc"))
except Exception:
 errors.append(("third_party_versions.json","invalid upstream pins"))
if errors:
 print("REPOSITORY_AUDIT_FAILED",len(errors))
 for path,issue in errors[:70]:print("  "+path+" :: "+issue)
 sys.exit(1)
print("REPOSITORY_AUDIT_PASSED",count,"safe source/docs files")
