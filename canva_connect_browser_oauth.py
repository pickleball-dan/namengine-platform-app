import base64
import hashlib
import http.server
import json
import os
import secrets
import socketserver
import subprocess
import threading
import urllib.parse
import urllib.request
from pathlib import Path

PORT = 53682
REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback"
HOME_URI = f"http://127.0.0.1:{PORT}/"
SCOPES = "asset:read asset:write design:content:write design:meta:read"
TOKEN_PATH = Path(".canva-connect-token.json")
DEFAULT_CLIENT_ID = "OC-AaAWy7B27BHX"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def html(body: str) -> bytes:
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Canva Connect OAuth</title>
<style>body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:48px;max-width:760px}}input{{width:100%;padding:10px;margin:6px 0 16px;font-size:16px}}button{{padding:12px 18px;font-size:16px;background:#7d2cff;color:white;border:0;border-radius:8px}}code{{background:#f3f3f3;padding:2px 4px}}</style></head><body>{body}</body></html>""".encode("utf-8")


def post_form(url: str, data: dict, client_id: str, client_secret: str) -> dict:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(url, data=encoded, headers={
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")

state = {"client_id": None, "client_secret": None, "oauth_state": None, "code_verifier": None, "done": False, "error": None}

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def send_html(self, body: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html(body))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_html(f"""
<h1>Canva Connect setup</h1>
<p>Enter the Canva integration credentials. This page is local-only on <code>127.0.0.1</code>.</p>
<form method='post' action='/credentials'>
<label>Client ID</label><input name='client_id' value='{DEFAULT_CLIENT_ID}' autocomplete='off'>
<label>Client Secret</label><input name='client_secret' type='password' autocomplete='off' autofocus>
<button type='submit'>Continue to Canva authorization</button>
</form>
<p>Redirect URI configured in Canva should be: <code>{REDIRECT_URI}</code></p>
""")
            return
        if parsed.path == "/callback":
            qs = urllib.parse.parse_qs(parsed.query)
            code = qs.get("code", [None])[0]
            got_state = qs.get("state", [None])[0]
            err = qs.get("error", [None])[0]
            if err:
                state["error"] = f"Canva returned error: {err}"
                self.send_html(f"<h1>Canva error</h1><p>{err}</p>", 400)
                state["done"] = True
                return
            if not code or got_state != state.get("oauth_state"):
                state["error"] = "Missing authorization code or state mismatch."
                self.send_html("<h1>Authorization failed</h1><p>Missing code or state mismatch.</p>", 400)
                state["done"] = True
                return
            try:
                token = post_form("https://api.canva.com/rest/v1/oauth/token", {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "code_verifier": state["code_verifier"],
                }, state["client_id"], state["client_secret"])
                saved = dict(token)
                saved["client_id"] = state["client_id"]
                saved["client_secret"] = state["client_secret"]
                TOKEN_PATH.write_text(json.dumps(saved, indent=2), encoding="utf-8")
                self.send_html(f"<h1>Connected ✅</h1><p>Token saved locally to <code>{TOKEN_PATH}</code>. You can close this tab.</p>")
                state["done"] = True
            except Exception as e:
                state["error"] = str(e)
                self.send_html(f"<h1>Token exchange failed</h1><pre>{str(e)}</pre>", 500)
                state["done"] = True
            return
        self.send_html("<h1>Not found</h1>", 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/credentials":
            self.send_html("<h1>Not found</h1>", 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        data = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))
        client_id = (data.get("client_id", [""])[0]).strip()
        client_secret = (data.get("client_secret", [""])[0]).strip()
        if not client_id or not client_secret:
            self.send_html("<h1>Missing credentials</h1><p>Go back and enter both fields.</p>", 400)
            return
        state["client_id"] = client_id
        state["client_secret"] = client_secret
        state["code_verifier"] = b64url(secrets.token_bytes(96))
        state["oauth_state"] = b64url(secrets.token_bytes(48))
        code_challenge = b64url(hashlib.sha256(state["code_verifier"].encode("ascii")).digest())
        auth_url = "https://www.canva.com/api/oauth/authorize?" + urllib.parse.urlencode({
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "scope": SCOPES,
            "response_type": "code",
            "client_id": client_id,
            "state": state["oauth_state"],
            "redirect_uri": REDIRECT_URI,
        })
        self.send_response(302)
        self.send_header("Location", auth_url)
        self.end_headers()


def open_url(url: str):
    try:
        os.startfile(url)  # type: ignore[attr-defined]
    except Exception:
        subprocess.run(["cmd", "/c", "start", "", url], check=False)

if __name__ == "__main__":
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Open {HOME_URI}")
        open_url(HOME_URI)
        while not state["done"]:
            httpd.handle_request()
        if state.get("error"):
            print("ERROR:", state["error"])
            raise SystemExit(1)
        print(f"Saved token to {TOKEN_PATH}")
