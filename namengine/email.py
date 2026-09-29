"""Resend email integration for NamEngine magic links."""

from __future__ import annotations

import os
from typing import Any

import resend

FROM_ADDRESS = "NamEngine <support@nam-engine.com>"


def _api_key() -> str:
    key = os.getenv("RESEND_API_KEY", "")
    if not key:
        raise RuntimeError("RESEND_API_KEY environment variable is not set")
    return key


def send_magic_link(
    *,
    to_email: str,
    magic_url: str,
    vertical_name: str,
) -> dict[str, Any]:
    """Send a magic link email via Resend. Returns the Resend API response dict."""

    # In local dev, skip the real API call and just print the link
    if os.getenv("NAMENGINE_DEV_EMAIL") == "1":
        print(f"\n[DEV MAGIC LINK] To: {to_email}\n[DEV MAGIC LINK] URL: {magic_url}\n")
        return {"id": "dev-mode"}

    resend.api_key = _api_key()

    subject = f"Your {vertical_name} names — pick up where you left off"

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f8f9fa;font-family:system-ui,-apple-system,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8f9fa;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.06);">

          <!-- Header -->
          <tr>
            <td style="padding:32px 40px 24px;border-bottom:1px solid #f0f0f0;">
              <p style="margin:0;font-size:13px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#999;">NamEngine</p>
              <h1 style="margin:8px 0 0;font-size:22px;font-weight:700;color:#111;line-height:1.3;">Your {vertical_name} names are waiting</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:28px 40px;">
              <p style="margin:0 0 20px;font-size:15px;color:#444;line-height:1.6;">
                Click the button below to get back to your names. Your reactions and progress are saved exactly where you left them.
              </p>
              <p style="margin:0 0 28px;font-size:15px;color:#444;line-height:1.6;">
                You can also share this link with a partner so they can see your list and weigh in.
              </p>

              <!-- CTA -->
              <table cellpadding="0" cellspacing="0" style="margin:0 auto 28px;">
                <tr>
                  <td style="border-radius:10px;background:#ff5233;">
                    <a href="{magic_url}" style="display:inline-block;padding:16px 36px;font-size:15px;font-weight:700;color:#fff;text-decoration:none;border-radius:10px;">
                      Open My Names →
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Link fallback -->
              <p style="margin:0 0 8px;font-size:12px;color:#999;text-align:center;">Or copy this link:</p>
              <p style="margin:0;font-size:12px;color:#3b82f6;text-align:center;word-break:break-all;">
                <a href="{magic_url}" style="color:#3b82f6;">{magic_url}</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px 28px;border-top:1px solid #f0f0f0;">
              <p style="margin:0;font-size:11px;color:#bbb;text-align:center;line-height:1.6;">
                This link expires in 30 days. You didn't need to create a password — that's intentional.<br>
                Questions? Reply to this email and we'll help.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    text_body = f"""Your {vertical_name} names are waiting.

Click the link below to pick up where you left off. Your reactions and progress are saved.

You can also share this link with a partner.

{magic_url}

This link expires in 30 days.
Questions? Reply to this email.

— NamEngine
"""

    params: resend.Emails.SendParams = {
        "from": FROM_ADDRESS,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }

    email = resend.Emails.send(params)
    return email
