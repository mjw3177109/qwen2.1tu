"""Fix the legacy ComfyUI-GGUF plugin in an existing Colab Qwen Image 2.1 session.

No model weights are downloaded or changed. Does not access GitHub secrets.
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path('/content/qwen21_light')
COMFY = ROOT / 'ComfyUI'
NODE = COMFY / 'custom_nodes' / 'ComfyUI-GGUF'
BACKUP = ROOT / 'backups' / 'ComfyUI-GGUF-city96'
REPO = 'https://github.com/leejet/ComfyUI-GGUF.git'
OUTPUT = Path('/content/qwen21_outputs')
URL = 'http://127.0.0.1:8188'


def run(*cmd):
    print('$', ' '.join(map(str, cmd)))
    subprocess.run(list(map(str, cmd)), check=True)


def healthy():
    try:
        return requests.get(URL + '/system_stats', timeout=3).ok
    except requests.RequestException:
        return False


def origin():
    if not (NODE / '.git').exists():
        return ''
    p = subprocess.run(['git','-C',str(NODE),'remote','get-url','origin'], capture_output=True,text=True)
    return p.stdout.strip() if p.returncode == 0 else ''


if not (COMFY / 'main.py').is_file():
    raise RuntimeError(f'ComfyUI not present at {COMFY}. Run the existing notebook install cell first.')
if not list((COMFY / 'models' / 'diffusion_models').glob('*2.1*gguf')):
    print('Warning: Qwen-Image 2.1 GGUF weights not found at the expected location.')

if NODE.exists() and 'leejet/ComfyUI-GGUF' not in origin():
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if BACKUP.exists():
        shutil.rmtree(BACKUP)
    shutil.move(str(NODE),str(BACKUP))
    print('Backed up the old city96 GGUF plugin outside custom_nodes.')
if not NODE.exists():
    run('git','clone','--depth','1',REPO,NODE)
else:
    run('git','-C',NODE,'pull','--ff-only')

if (NODE / 'requirements.txt').is_file():
    run(sys.executable,'-m','pip','install','-q','--no-cache-dir','-r',NODE/'requirements.txt')
run(sys.executable,'-m','pip','install','-q','--no-cache-dir','psutil')
import psutil

if healthy():
    found = False
    for process in psutil.process_iter(['pid','cmdline']):
        try:
            cmdline = ' '.join(process.info.get('cmdline') or [])
            if 'main.py' in cmdline and '--port' in cmdline and '8188' in cmdline and str(process.cwd()) == str(COMFY):
                print('Stopping old ComfyUI process PID',process.pid)
                process.terminate()
                process.wait(timeout=15)
                found = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            continue
    time.sleep(2)
    if healthy():
        raise RuntimeError('Port 8188 is occupied by an unmanaged service. Restart the Colab runtime and run V5.1.')
    if not found:
        raise RuntimeError('Could not identify the old ComfyUI process. Restart the Colab runtime and run V5.1.')

OUTPUT.mkdir(parents=True, exist_ok=True)
(ROOT/'tmp').mkdir(parents=True, exist_ok=True)
(COMFY/'input').mkdir(parents=True, exist_ok=True)
log = ROOT / 'comfyui.log'
command = [sys.executable,'main.py','--listen','127.0.0.1','--port','8188','--lowvram',
           '--disable-auto-launch','--output-directory',str(OUTPUT),
           '--temp-directory',str(ROOT/'tmp'),'--input-directory',str(COMFY/'input')]
with log.open('a',encoding='utf-8') as f:
    process = subprocess.Popen(command,cwd=str(COMFY),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
for _ in range(90):
    if healthy():
        break
    if process.poll() is not None:
        break
    time.sleep(2)
if not healthy():
    print('Latest ComfyUI error log:')
    print('\n'.join(log.read_text(errors='replace').splitlines()[-65:]))
    raise RuntimeError('ComfyUI failed to restart; check the log output above.')

infos=requests.get(URL+'/object_info',timeout=40).json()
required=['UnetLoaderGGUF','TextEncodeQwenImage21','SamplerCustom','VAEDecode','SaveImage']
missing=[name for name in required if name not in infos]
if missing:
    raise RuntimeError('Missing ComfyUI nodes after repair: '+', '.join(missing))
rev=subprocess.check_output(['git','-C',str(NODE),'rev-parse','--short','HEAD'],text=True).strip()
print('SUCCESS: leejet/ComfyUI-GGUF @',rev,'has loaded in the running ComfyUI server.')
print('Existing model weights are unchanged. Return to the notebook and rerun its last queued-job execution cell.')
