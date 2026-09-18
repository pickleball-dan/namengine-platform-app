import urllib.request, re

req = urllib.request.Request('https://nam-engine.com/baby', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    html = r.read().decode()

tags = re.findall(r'<meta[^>]+(?:property|name)=["\']([^"\']+)["\'][^>]+content=["\']([^"\']+)["\']', html)
for name, val in tags:
    if name.startswith('og:') or name.startswith('twitter:'):
        print(f'{name} = {val}')
