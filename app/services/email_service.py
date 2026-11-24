"""Email notification service for account confirmation and security alerts."""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.core.config import settings
from app.schemas.auth import SentEmailRecord

logger = logging.getLogger("reviewpilot.email")


def _send_smtp_email(to_email: str, subject: str, html_content: str, text_content: str) -> bool:
    """Send email via SMTP if configured."""
    if not settings.smtp_host or not settings.smtp_user:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from_email
        msg["To"] = to_email

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
        logger.info(f"Dispatched SMTP email to {to_email} with subject '{subject}'")
        return True
    except Exception as e:
        logger.warning(f"SMTP delivery failed to {to_email}: {e}. Falling back to system email log.")
        return False


def send_signup_confirmation_email(
    to_email: str,
    username: str,
    full_name: str | None = None,
    storage_repo: Any = None,
) -> SentEmailRecord:
    """Generate and dispatch welcome & account confirmation email."""
    name_display = full_name or username
    subject = "Welcome to ReviewPilot — Confirm Your Account"

    text_body = f"""Hello {name_display},

Welcome to ReviewPilot — Next-Gen Autonomous AI Code Reviewer!

Your developer account (@{username}) has been successfully created and confirmed.

Key Features Available:
• Multi-Agent PR Review (Security, Bugs, Style, Architecture)
• Universal Repository Connector (Any public repo, commit, or pull request)
• Direct Multi-Language Code Runner (Python, JS/TS, Go, Rust, Java, C++)
• Automated Quality Scoring & Actionable Suggestions

You can start reviewing code immediately by visiting:
https://ai-code-reviewer-ui-eq6s.onrender.com

Happy Coding!
The ReviewPilot Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Welcome to ReviewPilot</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0b1220; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0b1220; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="600" border="0" cellspacing="0" cellpadding="0" style="background: #0f172a; border-radius: 16px; border: 1px solid #1e293b; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
          <!-- Header -->
          <tr>
            <td style="padding: 32px 40px; background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.15)); border-bottom: 1px solid #1e293b;">
              <div style="font-size: 24px; font-weight: 800; color: #818cf8; letter-spacing: -0.5px; display: inline-flex; align-items: center;">
                <span>🛡️ ReviewPilot AI</span>
              </div>
              <div style="color: #94a3b8; font-size: 13px; margin-top: 4px;">
                Autonomous Code Quality & Security Review Platform
              </div>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding: 36px 40px;">
              <h1 style="font-size: 22px; font-weight: 700; color: #f8fafc; margin-top: 0; margin-bottom: 16px;">
                Welcome aboard, {name_display}! 🎉
              </h1>
              <p style="font-size: 15px; line-height: 1.6; color: #cbd5e1; margin-bottom: 24px;">
                Your account (<strong style="color: #38bdf8;">@{username}</strong>) has been registered and verified. You are all set to audit repositories, inspect pull requests, and catch vulnerabilities before deployment.
              </p>

              <div style="background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; margin-bottom: 28px;">
                <div style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin-bottom: 12px;">
                  🚀 What You Can Do Now:
                </div>
                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                  <tr>
                    <td style="padding: 6px 0; color: #94a3b8; font-size: 13px;">
                      🔍 <strong style="color: #f1f5f9;">Universal GitHub Auditing</strong> — Review any public repo or pull request URL
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #94a3b8; font-size: 13px;">
                      ⚡ <strong style="color: #f1f5f9;">Direct Code Playground</strong> — Test multi-language snippets in Python, Go, Rust, JS & Java
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #94a3b8; font-size: 13px;">
                      🛡️ <strong style="color: #f1f5f9;">Multi-Agent Intelligence</strong> — Security, syntax, performance & regression analysis
                    </td>
                  </tr>
                </table>
              </div>

              <div style="text-align: center; margin: 32px 0 20px;">
                <a href="https://ai-code-reviewer-ui-eq6s.onrender.com" style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 10px; font-weight: 600; font-size: 15px; display: inline-block; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);">
                  Launch ReviewPilot Dashboard →
                </a>
              </div>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding: 24px 40px; background: #090e17; border-top: 1px solid #1e293b; text-align: center; color: #64748b; font-size: 12px; line-height: 1.5;">
              This confirmation email was sent to <span style="color: #94a3b8;">{to_email}</span>.<br>
              © 2026 ReviewPilot AI. All rights reserved.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    sent_via_smtp = _send_smtp_email(to_email, subject, html_body, text_body)
    status = "delivered_smtp" if sent_via_smtp else "delivered_system"

    if storage_repo:
        return storage_repo.save_sent_email(
            recipient=to_email,
            subject=subject,
            body_html=html_body,
            body_text=text_body,
            email_type="signup_confirmation",
            status=status,
        )
    return SentEmailRecord(
        id="eml_preview",
        recipient=to_email,
        subject=subject,
        body_html=html_body,
        body_text=text_body,
        email_type="signup_confirmation",
        status=status,
    )


def send_signin_notification_email(
    to_email: str,
    username: str,
    ip_address: str = "Unknown",
    user_agent: str = "Web Browser",
    storage_repo: Any = None,
) -> SentEmailRecord:
    """Generate and dispatch login confirmation / security notification email."""
    subject = "Security Notice: Successful Sign-In to ReviewPilot"

    text_body = f"""Hello @{username},

You have successfully signed in to your ReviewPilot account.

Login Details:
• Client / Device: {user_agent}
• IP Address: {ip_address}

If you initiated this sign-in, no action is required. If you did not log in, please secure your credentials.

Best regards,
ReviewPilot Security Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin: 0; padding: 0; background-color: #0b1220; font-family: -apple-system, BlinkMacSystemFont, sans-serif; color: #f8fafc;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="padding: 30px 15px;">
    <tr>
      <td align="center">
        <table width="560" border="0" cellspacing="0" cellpadding="0" style="background: #0f172a; border-radius: 12px; border: 1px solid #1e293b; padding: 30px;">
          <tr>
            <td>
              <div style="font-size: 20px; font-weight: 700; color: #38bdf8; margin-bottom: 16px;">
                🔔 New Sign-In Confirmation
              </div>
              <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6;">
                Hello <strong style="color: #f8fafc;">@{username}</strong>,<br>
                You recently signed in to ReviewPilot. Here are the session details:
              </p>
              <div style="background: #1e293b; border-radius: 8px; padding: 16px; margin: 20px 0; font-size: 13px; color: #94a3b8; border: 1px solid #334155;">
                <p style="margin: 4px 0;"><strong style="color: #e2e8f0;">Device / Browser:</strong> {user_agent}</p>
                <p style="margin: 4px 0;"><strong style="color: #e2e8f0;">IP Address:</strong> {ip_address}</p>
                <p style="margin: 4px 0;"><strong style="color: #e2e8f0;">Status:</strong> <span style="color: #34d399;">Authenticated Successfully</span></p>
              </div>
              <p style="color: #64748b; font-size: 12px;">
                If this was you, you can safely disregard this email.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    sent_via_smtp = _send_smtp_email(to_email, subject, html_body, text_body)
    status = "delivered_smtp" if sent_via_smtp else "delivered_system"

    if storage_repo:
        return storage_repo.save_sent_email(
            recipient=to_email,
            subject=subject,
            body_html=html_body,
            body_text=text_body,
            email_type="signin_notification",
            status=status,
        )
    return SentEmailRecord(
        id="eml_signin_preview",
        recipient=to_email,
        subject=subject,
        body_html=html_body,
        body_text=text_body,
        email_type="signin_notification",
        status=status,
    )
