"""Offline entry point; recompute data, figures, documents and regression checks."""
from pathlib import Path
import subprocess,sys,hashlib,json,platform,importlib.metadata
R=Path(__file__).resolve().parents[1]
for cmd in [[sys.executable,str(R/'src/build.py')],[sys.executable,str(R/'src/write_documents.py')],[sys.executable,'-m','unittest','discover','-s',str(R/'tests'),'-v']]:
 run=subprocess.run(cmd,cwd=R,text=True,capture_output=True)
 if run.returncode:
  print(run.stdout);print(run.stderr,file=sys.stderr);raise SystemExit(run.returncode)
 if 'unittest' in cmd:(R/'outputs/test_results.txt').write_text(run.stdout+run.stderr)
env={'python':platform.python_version(),'packages':{p:importlib.metadata.version(p) for p in ['numpy','pandas','matplotlib','python-docx']}}
(R/'environment.json').write_text(json.dumps(env,indent=2))
checks={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.rglob('*')) if p.is_file() and '__pycache__' not in str(p) and p.suffix!='.pyc' and p.name!='SHA256.json'}
(R/'SHA256.json').write_text(json.dumps(checks,indent=2))
print('Built annual scenarios, sensitivity cases, figures and methods documents. See outputs/test_results.txt.')
