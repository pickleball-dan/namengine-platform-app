import base64
import hashlib
import http.server
import json
import os
import secrets
import socketserver
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
from getpass import getpass
from pathlib import Path

PORT = 53682
REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback"
SCOPES = "asset:write design:content:write design:meta:read"
TOKEN_PATH = Path(".canva-connect-token.json")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def post_form(url: str, data: dict, client_id: str, client_secret: str) -> dict:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")


def main():
    print("Canva Connect OAuth helper")
    print(f"Redirect URI must match Canva Developer Portal: {REDIRECT_URI}")
    client_id = os.environ.get("CANVA_CONNECT_CLIENT_ID") or input("Client ID: ").strip()
    client_secret = os.environ.get("CANVA_CONNECT_CLIENT_SECRET") or getpass("Client secret: ").strip()
    if not client_id or not client_secret:
        raise SystemExit("Missing client ID/secret")

    code_verifier = b64url(secrets.token_bytes(96))
    code_challenge = b64url(hashlib.sha256(code_verifier.encode("ascii")).digest())
    state = b64url(secrets.token_bytes(48))
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            qs = urllib.parse.parse_qs(parsed.query)
            result["code"] = qs.get("code", [None])[0]
            result["state"] = qs.get("state", [None])[0]
            result["error"] = qs.get("error", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h1>Canva authorization received.</h1><p>You can close this tab.</p>")

    auth_url = "https://www.canva.com/api/oauth/authorize?" + urllib.parse.urlencode({
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": SCOPES,
        "response_type": "code",
        "client_id": client_id,
        "state": state,
        "redirect_uri": REDIRECT_URI,
    })

    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        thread = threading.Thread(target=httpd.handle_request, daemon=True)
        thread.start()
        print("Opening Canva authorization URL...")
        try:
            os.startfile(auth_url)  # type: ignore[attr-defined]
        except Exception:
            subprocess.run(["cmd", "/c", "start", "", auth_url], check=False)
        print("Waiting for Canva callback...")
        thread.join(timeout=300)

    if result.get("error"):
        raise SystemExit(f"Canva returned error: {result['error']}")
    if not result.get("code"):
        raise SystemExit("No authorization code received before timeout.")
    if result.get("state") != state:
        raise SystemExit("State mismatch; refusing token exchange.")

    token = post_form("https://api.canva.com/rest/v1/oauth/token", {
        "grant_type": "authorization_code",
        "code": result["code"],
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }, client_id, client_secret)

    safe = dict(token)
    safe["client_id"] = client_id
    safe["client_secret"] = client_secret
    TOKEN_PATH.write_text(json.dumps(safe, indent=2), encoding="utf-8")
    print(f"Saved token to {TOKEN_PATH}")
    print("Scopes/token response keys:", ", ".join(sorted(token.keys())))


if __name__ == "__main__":
    main()
