"""Qwen-Image-2.1 GitHub image edit batch intake for interactive Google Colab.

Provides deterministic, validated ZIP -> jobs/inputs/*.jpg.b64 and
jobs/pending/*.json. This does not perform inference or prompt optimization.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import posixpath
import re
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests

SUPPORTED_IMAGES = {'.jpg', '.jpeg', '.png', '.webp'}
SUPPORTED_TEXT = {'.txt', '.md'}
MAX_FILES = 500
MAX_JOBS = 100
MAX_UNCOMPRESSED = 150_000_000
MAX_IMAGE = 4_000_000
DEFAULT_RESOLUTION = 512
DEFAULT_SEED = 42

class BatchValidationError(ValueError):
    pass


def _norm(path: str) -> str:
    path = path.replace('\\', '/')
    if path.startswith('./'):
        path = path[2:]
    if not path or path.startswith('/') or '..' in path.split('/') or ':' in path:
        raise BatchValidationError('非法 ZIP 文件路径: ' + path)
    return posixpath.normpath(path)


def _read_text(raw: bytes, name: str) -> str:
    if len(raw) > 150_000:
        raise BatchValidationError('文本过大: ' + name)
    return raw.decode('utf-8-sig').strip()


def _clean_key(stem: str) -> str:
    # Prefixes are removed only for matching images and prompts.
    stem = re.sub(r'^(?:原图|母图|源图|提示词|编辑提示词|图片|source|input|image|prompt)[_\-\s]*', '', stem, flags=re.I)
    return stem.strip().casefold()


def _make_id(key: str, raw: bytes, prompt: str, used: set[str]) -> str:
    slug = re.sub(r'[^A-Za-z0-9_-]+', '_', key).strip('_')[:30]
    if not slug:
        slug = 'image'
    digest = hashlib.sha256(raw + prompt.encode('utf-8')).hexdigest()[:10]
    job_id = f'edit_{slug}_{digest}'
    if job_id in used:
        raise BatchValidationError('重复任务 ID: ' + job_id)
    used.add(job_id)
    return job_id


def _check_id(job_id: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,64}', job_id):
        raise BatchValidationError('task_id 必须为 8-64 位英文/数字/_/-: ' + job_id)
    return job_id


def _index_zip(zip_path: str | Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(zip_path) as zf:
        info_list = [i for i in zf.infolist() if not i.is_dir() and not i.filename.startswith('__MACOSX/')]
        if len(info_list) > MAX_FILES:
            raise BatchValidationError('ZIP 中文件超过上限: ' + str(MAX_FILES))
        if sum(i.file_size for i in info_list) > MAX_UNCOMPRESSED:
            raise BatchValidationError('ZIP 展开体积过大，禁止解压')
        for info in info_list:
            p = _norm(info.filename)
            if p in files:
                raise BatchValidationError('ZIP 内重复文件名: ' + p)
            files[p] = zf.read(info)
    if not files:
        raise BatchValidationError('ZIP 为空')
    return files


def _strip_root(files: dict[str, bytes]) -> dict[str, bytes]:
    # Folders zipped in Finder/Explorer often include one enclosing root.
    parts = [p.split('/') for p in files]
    if all(len(p) >= 2 for p in parts) and len({p[0] for p in parts}) == 1:
        return {'/'.join(p.split('/')[1:]): b for p, b in files.items()}
    return files


def _image_files(files: dict[str, bytes]) -> list[str]:
    result = []
    for name in files:
        path = Path(name)
        if name.startswith(('references/', 'reference/', 'masks/', 'mask/')):
            raise BatchValidationError('包含参考图或遮罩：当前 V5 仅支持单张母图，不允许静默忽略 ' + name)
        if path.suffix.lower() in SUPPORTED_IMAGES:
            if name.startswith(('sources/', 'images/', 'inputs/', 'mother/', '母图/')) or '/' not in name:
                result.append(name)
            else:
                raise BatchValidationError('未知图片目录，无法判断是否是母图：' + name)
    return sorted(result)


def _prompt_files(files: dict[str, bytes]) -> list[str]:
    reserved = {'global_rules.txt', 'batch_prompt.txt', 'common_prompt.txt', '统一修改.txt', 'README.md', '说明.md'}
    return sorted(p for p in files if Path(p).suffix.lower() in SUPPORTED_TEXT
                  and (p.startswith('prompts/') or '/' not in p)
                  and Path(p).name not in reserved)


def _get_optional(files, names):
    matched = [x for x in names if x in files]
    if len(matched) > 1:
        raise BatchValidationError('多个全局文件冲突: ' + str(matched))
    return _read_text(files[matched[0]], matched[0]) if matched else ''


def prepare_batch(zip_path: str | Path) -> dict:
    """Return validated in-memory task records. No GitHub writes yet."""
    files = _strip_root(_index_zip(zip_path))
    global_rules = _get_optional(files, ['global_rules.txt', 'prompts/global_rules.txt'])
    batch_prompt = _get_optional(files, ['batch_prompt.txt', 'common_prompt.txt', '统一修改.txt', 'prompts/batch_prompt.txt'])
    images = _image_files(files)
    prompts = _prompt_files(files)
    manifest_files = [p for p in ('batch.csv', 'tasks.csv') if p in files]
    if len(manifest_files) > 1:
        raise BatchValidationError('只能有一个 batch.csv/tasks.csv')
    if not images:
        raise BatchValidationError('没有找到母图：放入 sources/*.png/jpg/webp')

    rows = []
    if manifest_files:
        csv_name = manifest_files[0]
        reader = csv.DictReader(io.StringIO(_read_text(files[csv_name], csv_name)))
        if not reader.fieldnames or 'source' not in reader.fieldnames:
            raise BatchValidationError('CSV 必须包含 source 列')
        for lineno, row in enumerate(reader, start=2):
            source = _norm((row.get('source') or '').strip())
            if source not in images:
                raise BatchValidationError(f'CSV 第 {lineno} 行找不到母图: {source}')
            prompt_file = (row.get('prompt_file') or '').strip()
            prompt = (row.get('prompt') or '').strip()
            if prompt_file and prompt:
                raise BatchValidationError(f'CSV 第 {lineno} 行 prompt 和 prompt_file 只能选一种')
            if prompt_file:
                prompt_file = _norm(prompt_file)
                if prompt_file not in files or Path(prompt_file).suffix.lower() not in SUPPORTED_TEXT:
                    raise BatchValidationError(f'CSV 第 {lineno} 行找不到提示词: {prompt_file}')
                prompt = _read_text(files[prompt_file], prompt_file)
            if not prompt:
                prompt = batch_prompt
            raw_id = (row.get('task_id') or '').strip()
            if not raw_id:
                raw_id = None
            resolution = int((row.get('resolution') or DEFAULT_RESOLUTION))
            seed = int((row.get('seed') or DEFAULT_SEED))
            rows.append((raw_id, source, prompt, resolution, seed))
    else:
        prompt_map = {}
        for p in prompts:
            key = _clean_key(Path(p).stem)
            if key in prompt_map:
                raise BatchValidationError('提示词文件名存在二义性: ' + p + ' 和 ' + prompt_map[key])
            prompt_map[key] = p
        image_keys = {}
        used_prompts = set()
        for src in images:
            key = _clean_key(Path(src).stem)
            if key in image_keys:
                raise BatchValidationError('母图重名造成匹配歧义: ' + src + ' 和 ' + image_keys[key])
            image_keys[key] = src
            text_file = prompt_map.get(key)
            if text_file:
                used_prompts.add(text_file)
                prompt = _read_text(files[text_file], text_file)
            elif len(images) == len(prompts) == 1 and not batch_prompt:
                text_file = prompts[0]
                used_prompts.add(text_file)
                prompt = _read_text(files[text_file], text_file)
            else:
                prompt = batch_prompt
            rows.append((None, src, prompt, DEFAULT_RESOLUTION, DEFAULT_SEED))
        orphans = set(prompts) - used_prompts
        if orphans:
            raise BatchValidationError('发现未配对的提示词，拒绝猜测: ' + ', '.join(sorted(orphans)))

    if len(rows) > MAX_JOBS:
        raise BatchValidationError('任务数量超过本批上限: ' + str(MAX_JOBS))
    results, used = [], set()
    for raw_id, src, prompt, resolution, seed in rows:
        if not 3 <= len(prompt) <= 2200:
            raise BatchValidationError('编辑要求为空/过长: ' + src)
        if resolution not in (512, 640, 768):
            raise BatchValidationError('目前 GPU 工作流支持 512/640/768，发现 ' + str(resolution))
        if not 0 <= seed < 2**64:
            raise BatchValidationError('seed 必须是无符号 64 位整数')
        raw = files[src]
        if not raw or len(raw) > MAX_IMAGE:
            raise BatchValidationError('母图必须小于等于 4MB：' + src)
        if raw_id:
            job_id = _check_id(raw_id)
            if job_id in used:
                raise BatchValidationError('重复 task_id: ' + job_id)
            used.add(job_id)
        else:
            job_id = _make_id(_clean_key(Path(src).stem), raw, prompt, used)
        ext = Path(src).suffix.lower().lstrip('.')
        if ext == 'jpeg':
            ext = 'jpg'
        final_prompt = '<image1> ' + prompt.removeprefix('<image1>').strip()
        if global_rules:
            final_prompt += '\n全局一致性约束：' + global_rules
        final_prompt += ('\n仅修改用户明确要求的区域。除明确指定的变化外，优先保持原始人物身份、'
                         '身体比例、设备布局、场景光照、镜头视角及摄影/绘画风格，不擅自添加物体。')
        if len(final_prompt) > 2500:
            raise BatchValidationError('组合提示词过长: ' + job_id)
        results.append({
            'id': job_id, 'source': src,
            'input_b64_path': f'jobs/inputs/{job_id}.{ext}.b64',
            'input_sha256': hashlib.sha256(raw).hexdigest(),
            'raw_b64': base64.b64encode(raw).decode('ascii'),
            'prompt': final_prompt, 'resolution': resolution, 'seed': seed,
        })
    return {'jobs': results, 'source_zip': Path(zip_path).name,
            'count': len(results), 'global_rules': bool(global_rules)}


def _api(session: requests.Session, repo: str, path: str) -> str:
    return f'https://api.github.com/repos/{repo}/contents/{path}'


def submit_batch(prepared: dict, repo: str, token: str, branch: str = 'main',
                 dry_run: bool = False) -> dict:
    """Submit validated inputs BEFORE pending JSONs; safe to rerun identical batch."""
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
        raise ValueError('不合法的 GitHub 仓库名')
    if not token and not dry_run:
        raise ValueError('请在 Colab Secrets 里设置 GITHUB_TOKEN')
    summary = []
    session = requests.Session()
    session.headers.update({
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    })

    def existing(path):
        r = session.get(_api(session, repo, path), params={'ref': branch}, timeout=30)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def create_checked(path, text):
        raw = text.encode('utf-8')
        blob_sha = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        current = existing(path)
        if current:
            if current.get('sha') != blob_sha:
                raise BatchValidationError('GitHub 存在不同内容的同名文件，拒绝覆盖：' + path)
            return 'EXISTS'
        payload = {'message': f'jobs: add {path}', 'branch': branch,
                   'content': base64.b64encode(raw).decode('ascii')}
        r = session.put(_api(session, repo, path), json=payload, timeout=120)
        if r.status_code not in (200, 201):
            raise RuntimeError(f'GitHub 写入失败 {path} HTTP {r.status_code}: {r.text[:220]}')
        verified = existing(path)
        if verified is None or verified.get('sha') != blob_sha:
            raise RuntimeError('回读 SHA 验证失败：' + path)
        return 'CREATED'

    for i, job in enumerate(prepared['jobs'], start=1):
        jid = job['id']
        rec = {
            'schema_version': 1, 'id': jid, 'kind': 'image_edit',
            'input_b64_path': job['input_b64_path'],
            'input_sha256': job['input_sha256'],
            'prompt': job['prompt'], 'resolution': job['resolution'], 'seed': job['seed'],
            'created_at': 'queued_by_colab',
        }
        src_path = job['input_b64_path']
        pending_path = f'jobs/pending/{jid}.json'
        if dry_run:
            summary.append({'id': jid, 'source': src_path, 'status': 'DRY_RUN'})
            continue
        image_status = create_checked(src_path, job['raw_b64'])
        pending_status = create_checked(pending_path, json.dumps(rec, ensure_ascii=False, indent=2)+'\n')
        summary.append({'id': jid, 'source': image_status,
                        'pending': pending_status, 'status': 'QUEUED'})
        print(f'[{i}/{prepared["count"]}] 已入队：{jid}，母图={image_status}，任务={pending_status}')
        time.sleep(0.3)
    return {'submitted': len(summary), 'details': summary}


def preview_as_text(prepared: dict) -> str:
    lines = [f'检测到 {prepared["count"]} 张待编辑图片（未生成图像）']
    for item in prepared['jobs']:
        lines.append(f'  {item["id"]}: {item["source"]} -> images/{item["id"]}.png')
    return '\n'.join(lines)