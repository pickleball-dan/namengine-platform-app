import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_PATH = Path('.canva-connect-token.json')
BASE = Path('design-references/social-launch/batch1-canva-templates')
OUT_PATH = BASE / 'canva-batch1-qa-fixed-designs.json'

FILES = [
    'template-01-reel-text-card-9x16.png',
    'template-02-if-you-love-carousel-4x5.png',
    'template-03-would-you-split-poll-9x16.png',
    'template-04-name-dna-explainer-9x16.png',
    'template-05-nobodys-talking-feature-4x5.png',
    'template-06-sunday-name-list-4x5.png',
    'day-01-why-namengine-exists-preview.png',
    'day-02-if-you-love-theodore-preview.png',
    'day-03-arthur-august-preview.png',
    'day-04-name-dna-margot-preview.png',
    'day-05-conrad-preview.png',
    'day-06-popularity-debate-preview.png',
    'day-07-classic-list-preview.png',
]

def load_token():
    return json.loads(TOKEN_PATH.read_text(encoding='utf-8'))

def save_token(token):
    TOKEN_PATH.write_text(json.dumps(token, indent=2), encoding='utf-8')

def request(method, url, token, headers=None, body=None):
    headers = dict(headers or {})
    headers['Authorization'] = f"Bearer {token['access_token']}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read().decode('utf-8', errors='replace')
            return resp.status, json.loads(data) if data else {}
    except urllib.error.HTTPError as e:
        data = e.read().decode('utf-8', errors='replace')
        try:
            parsed = json.loads(data)
        except Exception:
            parsed = data
        return e.code, parsed

def refresh(token):
    basic = base64.b64encode(f"{token['client_id']}:{token['client_secret']}".encode()).decode()
    body = urllib.parse.urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': token['refresh_token'],
    }).encode()
    req = urllib.request.Request('https://api.canva.com/rest/v1/oauth/token', data=body, headers={
        'Authorization': f'Basic {basic}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }, method='POST')
    with urllib.request.urlopen(req, timeout=30) as resp:
        new = json.loads(resp.read().decode())
    token.update(new)
    save_token(token)
    return token

def api(method, url, token, headers=None, body=None):
    status, data = request(method, url, token, headers, body)
    if status == 401 and token.get('refresh_token'):
        token = refresh(token)
        status, data = request(method, url, token, headers, body)
    return token, status, data

def title_from_filename(filename):
    stem = Path(filename).stem.replace('-preview', '')
    text = stem.replace('-', ' ').title().replace('Dna', 'DNA').replace('9X16', '9x16').replace('4X5', '4x5')
    return f"NamEngine Batch 1 QA fixed - {text}"

def upload_asset(token, path, name):
    image_bytes = path.read_bytes()
    metadata = json.dumps({'name_base64': base64.b64encode(name[:50].encode()).decode()})
    token, status, upload = api('POST', 'https://api.canva.com/rest/v1/asset-uploads', token, headers={
        'Content-Type': 'application/octet-stream',
        'Asset-Upload-Metadata': metadata,
        'Content-Length': str(len(image_bytes)),
    }, body=image_bytes)
    if status >= 300:
        raise RuntimeError(f'upload failed {status}: {upload}')
    job_id = upload.get('job', {}).get('id')
    if not job_id:
        raise RuntimeError(f'no job id: {upload}')
    for _ in range(20):
        time.sleep(1.5)
        token, js, job = api('GET', f'https://api.canva.com/rest/v1/asset-uploads/{job_id}', token)
        if js >= 300:
            raise RuntimeError(f'job read failed {js}: {job}')
        status_value = job.get('job', {}).get('status') or job.get('status')
        asset_id = job.get('job', {}).get('asset', {}).get('id') or job.get('asset', {}).get('id') or job.get('asset_id')
        if asset_id:
            return token, asset_id
        if status_value == 'failed':
            raise RuntimeError(f'upload job failed: {job}')
    raise RuntimeError('upload job timed out')

def create_design(token, asset_id, title):
    payload = json.dumps({
        'type': 'type_and_asset',
        'design_type': {'type': 'custom', 'width': 1080, 'height': 1350},
        'asset_id': asset_id,
        'title': title,
    }).encode()
    token, status, design = api('POST', 'https://api.canva.com/rest/v1/designs', token, headers={'Content-Type': 'application/json'}, body=payload)
    if status >= 300:
        raise RuntimeError(f'design create failed {status}: {design}')
    return token, design

def main():
    token = load_token()
    results = []
    for filename in FILES:
        path = BASE / filename
        if not path.exists():
            raise SystemExit(f'Missing {path}')
        title = title_from_filename(filename)
        print('Creating', title, flush=True)
        token, asset_id = upload_asset(token, path, title)
        token, design = create_design(token, asset_id, title)
        item = {
            'file': filename,
            'title': title,
            'asset_id': asset_id,
            'design_id': design.get('design', {}).get('id'),
            'edit_url': design.get('design', {}).get('urls', {}).get('edit_url'),
            'view_url': design.get('design', {}).get('urls', {}).get('view_url'),
        }
        results.append(item)
        OUT_PATH.write_text(json.dumps(results, indent=2), encoding='utf-8')
        print('  ->', item['design_id'], flush=True)
        time.sleep(1)
    print('WROTE', OUT_PATH)

if __name__ == '__main__':
    main()
