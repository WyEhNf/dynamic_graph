"""Download a public, immutable model revision; no remote Python is executed."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
from urllib.parse import quote


def verify_snapshot(root):
    root=Path(root)
    lock=json.loads((root/'model-lock.json').read_text(encoding='utf-8'))
    for name,info in lock['files'].items():
        path=root/name
        if not path.resolve().is_relative_to(root.resolve()): raise ValueError('invalid manifest file path')
        if not path.is_file() or path.stat().st_size!=info['bytes']: raise ValueError(f'model file size mismatch: {name}')
        with path.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=info['sha256']: raise ValueError(f'model file checksum mismatch: {name}')
    return lock


def modelscope_snapshot(repo, root, revision=None):
    import requests
    lock_path = root / 'model-lock.json'
    manifest=Path('artifacts') / ('model-lock.json' if repo=='Qwen/Qwen2.5-Coder-0.5B-Instruct'
                                else repo.rpartition('/')[2]+'-model-lock.json')
    existing = json.loads(lock_path.read_text()) if lock_path.exists() else (json.loads(manifest.read_text()) if manifest.exists() else None)
    if existing and existing.get('source') == 'modelscope' and existing['repo'] == repo and (revision is None or revision==existing.get('requested_revision')):
        lock = existing
    else:
        response = requests.get(f'https://modelscope.cn/api/v1/models/{repo}/repo/files',
                                params={'Revision':revision or 'master','Recursive':'true'}, timeout=60)
        response.raise_for_status()
        files = response.json()['Data']['Files']
        chosen = [f for f in files if f['Type']=='blob' and
                  (f['Path'].endswith(('.json','.safetensors')) or f['Path'] in {'merges.txt','README.md','LICENSE'})]
        lock = {'repo':repo, 'source':'modelscope', 'revision':'per-file immutable commits in files', 'requested_revision':revision,
                'origin':'official Qwen public ModelScope repository', 'files':{
                    f['Path']:{'revision':f['Revision'],'bytes':f['Size'],'sha256':f['Sha256']} for f in chosen}}
        lock_path.write_text(json.dumps(lock, indent=2), encoding='utf-8')
    for name, info in lock['files'].items():
        target = root / name
        if not target.resolve().is_relative_to(root.resolve()): raise ValueError('invalid model file path')
        if target.exists() and target.stat().st_size==info['bytes']:
            with target.open('rb') as stream: matching=hashlib.file_digest(stream,'sha256').hexdigest()==info['sha256']
            if matching: continue
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix+'.partial')
        url = f'https://modelscope.cn/api/v1/models/{repo}/repo?Revision={quote(info["revision"])}&FilePath={quote(name)}'
        for attempt in range(3):
            try:
                offset = partial.stat().st_size if partial.exists() else 0
                with requests.get(url, headers={'Range':f'bytes={offset}-'} if offset else {}, stream=True, timeout=(30,120)) as result:
                    result.raise_for_status()
                    if offset and result.status_code!=206: offset=0
                    with partial.open('ab' if offset else 'wb') as stream:
                        last = time.monotonic()
                        for chunk in result.iter_content(1024*1024):
                            stream.write(chunk); offset += len(chunk)
                            if time.monotonic()-last>10:
                                print(f'{name}: {offset}/{info["bytes"]} bytes', flush=True); last=time.monotonic()
                with partial.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
                if partial.stat().st_size!=info['bytes'] or digest!=info['sha256']: raise ValueError('model file checksum mismatch')
                partial.replace(target)
                print(f'Verified {name}: {info["bytes"]} bytes', flush=True)
                break
            except requests.RequestException:
                if attempt==2: raise
    lock['versions']={p:importlib.metadata.version(p) for p in ['torch','transformers','tokenizers','huggingface-hub','safetensors']}
    lock_path.write_text(json.dumps(lock, indent=2), encoding='utf-8')
    manifest.parent.mkdir(parents=True,exist_ok=True)
    manifest.write_text(json.dumps(lock,indent=2),encoding='utf-8')


def main():
    # Use the operating system's certificate store, retaining TLS verification.
    import truststore
    truststore.inject_into_ssl()
    from huggingface_hub import HfApi, snapshot_download
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', default='Qwen/Qwen2.5-Coder-0.5B-Instruct')
    parser.add_argument('--directory', default='models/qwen2.5-coder-0.5b-instruct')
    parser.add_argument('--revision', default=None)
    parser.add_argument('--source', choices=['huggingface','modelscope'], default='modelscope')
    args = parser.parse_args()
    root = Path(args.directory)
    root.mkdir(parents=True, exist_ok=True)
    if args.source == 'modelscope':
        modelscope_snapshot(args.repo, root,args.revision)
        print('Model snapshot ready.', flush=True)
        return
    lock_path = root / 'model-lock.json'
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else None
    revision = args.revision or (lock['revision'] if lock and lock['repo'] == args.repo and lock.get('source')=='huggingface' else HfApi().model_info(args.repo, token=False).sha)
    print(json.dumps({'repo':args.repo, 'revision':revision, 'directory':str(root.resolve())}), flush=True)
    lock = {'repo':args.repo, 'revision':revision, 'source':'huggingface', 'origin':'official public Hugging Face repository', 'files':{}}
    lock_path.write_text(json.dumps(lock, indent=2), encoding='utf-8')
    snapshot_download(args.repo, revision=revision, token=False, local_dir=str(root), max_workers=3,
                      allow_patterns=['*.json','*.safetensors','vocab.json','merges.txt','README.md','LICENSE'])
    for path in sorted(root.glob('*')):
        if path.is_file() and path != lock_path:
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                while chunk := stream.read(4*1024*1024): digest.update(chunk)
            lock['files'][path.name] = {'bytes':path.stat().st_size,'sha256':digest.hexdigest()}
    lock['versions'] = {p:importlib.metadata.version(p) for p in ['torch','transformers','tokenizers','huggingface-hub','safetensors']}
    lock_path.write_text(json.dumps(lock, indent=2), encoding='utf-8')
    print('Model snapshot ready.', flush=True)


if __name__ == '__main__': main()
