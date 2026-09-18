import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_PATH = Path('.canva-connect-token.json')
ASSET_PATH = Path('design-references/social-launch/batch1-canva-templates/day-01-why-namengine-exists-preview.png')
OUT_PATH = Path('design-references/social-launch/batch1-canva-templates/canva-connect-proof-result.json')


def load_token():
    return json.loads(TOKEN_PATH.read_text(encoding='utf-8'))


def save_token(token):
    TOKEN_PATH.write_text(json.dumps(token, indent=2), encoding='utf-8')


def request(method, url, token, headers=None, body=None, expect_json=True):
    headers = dict(headers or {})
    headers['Authorization'] = f"Bearer {token['access_token']}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read().decode('utf-8', errors='replace')
            return resp.status, json.loads(data) if expect_json and data else data
    except urllib.error.HTTPError as e:
        data = e.read().decode('utf-8', errors='replace')
        try:
            parsed = json.loads(data)
        except Exception:
            parsed = data
        return e.code, parsed


def refresh(token):
    client_id = token['client_id']
    client_secret = token['client_secret']
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
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


def main():
    if not TOKEN_PATH.exists():
        raise SystemExit('Missing .canva-connect-token.json')
    if not ASSET_PATH.exists():
        raise SystemExit(f'Missing {ASSET_PATH}')
    token = load_token()
    image_bytes = ASSET_PATH.read_bytes()
    name = 'NamEngine Day 01 Why NamEngine Exists'
    metadata = json.dumps({'name_base64': base64.b64encode(name.encode()).decode()})
    token, status, upload = api('POST', 'https://api.canva.com/rest/v1/asset-uploads', token, headers={
        'Content-Type': 'application/octet-stream',
        'Asset-Upload-Metadata': metadata,
        'Content-Length': str(len(image_bytes)),
    }, body=image_bytes)
    result = {'upload_status_code': status, 'upload_response': upload}
    print('UPLOAD_STATUS', status)
    print(json.dumps(upload, indent=2)[:2000])

    job_id = None
    if isinstance(upload, dict):
        job_id = upload.get('job', {}).get('id') or upload.get('id') or upload.get('job_id')
    asset_id = None
    if isinstance(upload, dict):
        asset_id = upload.get('asset', {}).get('id') or upload.get('asset_id')

    if job_id:
        for i in range(12):
            time.sleep(2)
            token, js, job = api('GET', f'https://api.canva.com/rest/v1/asset-uploads/{job_id}', token)
            print('JOB_STATUS', js, json.dumps(job)[:1000])
            result['job_status_code'] = js
            result['job_response'] = job
            if isinstance(job, dict):
                asset_id = (
                    job.get('asset', {}).get('id')
                    or job.get('asset_id')
                    or job.get('result', {}).get('asset', {}).get('id')
                    or job.get('job', {}).get('asset', {}).get('id')
                )
                status_value = job.get('job', {}).get('status') or job.get('status')
                if asset_id or status_value in ('success', 'failed'):
                    break
    if asset_id:
        payload = json.dumps({
            'type': 'type_and_asset',
            'design_type': {'type': 'custom', 'width': 1080, 'height': 1350},
            'asset_id': asset_id,
            'title': 'NamEngine Batch 1 - Day 01 proof'
        }).encode()
        token, ds, design = api('POST', 'https://api.canva.com/rest/v1/designs', token, headers={
            'Content-Type': 'application/json',
        }, body=payload)
        print('DESIGN_STATUS', ds)
        print(json.dumps(design, indent=2)[:2000])
        result['design_status_code'] = ds
        result['design_response'] = design
    else:
        print('NO_ASSET_ID_FOUND')
        result['blocked'] = 'No asset id found from upload/job response. May need asset:read scope to poll job result.'

    scrubbed = json.loads(json.dumps(result))
    OUT_PATH.write_text(json.dumps(scrubbed, indent=2), encoding='utf-8')
    print('WROTE', OUT_PATH)

if __name__ == '__main__':
    main()
