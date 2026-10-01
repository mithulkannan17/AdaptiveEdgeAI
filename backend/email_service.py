"""
AuraForest Email Dispatcher & Verification Service
==================================================

Handles automated email delivery of OTP verification codes, emergency security alerts,
and ranger dispatch notifications.

Features:
- Standards-compliant MIME Multipart (HTML + Plaintext) email generation.
- Real SMTP transmission via STARTTLS/SSL (configurable via environment variables).
- Local fallback outbox and audit logging for offline / sandbox testing.
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _load_env_file() -> None:
    """Auto-load key-value pairs from .env file and Streamlit st.secrets if present."""
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'").strip('"')
                    if k:
                        os.environ[k] = v
        except Exception:
            pass

    # Support Streamlit Community Cloud st.secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            for k, v in st.secrets.items():
                if isinstance(v, (str, int, float, bool)):
                    os.environ[str(k)] = str(v)
    except Exception:
        pass

_load_env_file()


class EmailService:
    """Dispatches verification OTPs and notification emails to users."""

    def __init__(self) -> None:
        self.reload_config()

    def reload_config(self) -> None:
        """Reload configuration from environment variables and Streamlit st.secrets."""
        _load_env_file()
        
        # Check Streamlit Cloud st.secrets directly
        st_user = ""
        st_pass = ""
        st_host = ""
        st_port = ""
        st_from = ""
        st_ssl = ""

        try:
            import streamlit as st
            if hasattr(st, "secrets") and st.secrets:
                # Top-level check
                st_user = str(st.secrets.get("SMTP_USER") or st.secrets.get("smtp_user") or "")
                st_pass = str(st.secrets.get("SMTP_PASS") or st.secrets.get("smtp_pass") or "")
                st_host = str(st.secrets.get("SMTP_HOST") or st.secrets.get("smtp_host") or "")
                st_port = str(st.secrets.get("SMTP_PORT") or st.secrets.get("smtp_port") or "")
                st_from = str(st.secrets.get("SMTP_FROM") or st.secrets.get("smtp_from") or "")
                st_ssl = str(st.secrets.get("SMTP_SSL") or st.secrets.get("smtp_ssl") or "")

                # Nested [smtp] / [SMTP] check if present
                if not st_user and ("smtp" in st.secrets or "SMTP" in st.secrets):
                    sec_dict = st.secrets.get("smtp") or st.secrets.get("SMTP") or {}
                    if isinstance(sec_dict, dict):
                        st_user = str(sec_dict.get("user") or sec_dict.get("SMTP_USER") or "")
                        st_pass = str(sec_dict.get("pass") or sec_dict.get("SMTP_PASS") or "")
                        st_host = str(sec_dict.get("host") or sec_dict.get("SMTP_HOST") or "")
                        st_port = str(sec_dict.get("port") or sec_dict.get("SMTP_PORT") or "")
                        st_from = str(sec_dict.get("from") or sec_dict.get("SMTP_FROM") or "")
        except Exception:
            pass

        self.smtp_host = (st_host or os.getenv("SMTP_HOST", "smtp.gmail.com")).strip()
        port_val = st_port or os.getenv("SMTP_PORT", "587")
        try:
            self.smtp_port = int(str(port_val).strip())
        except Exception:
            self.smtp_port = 587

        self.smtp_user = (st_user or os.getenv("SMTP_USER", "")).strip()
        raw_pass = (st_pass or os.getenv("SMTP_PASS", "")).strip()
        
        # Clean up spaces in 16-character Google App Passwords
        if "gmail" in self.smtp_host.lower():
            self.smtp_pass = raw_pass.replace(" ", "")
        else:
            self.smtp_pass = raw_pass

        self.smtp_from = (st_from or os.getenv("SMTP_FROM", self.smtp_user or "no-reply@auraforest.gov.in")).strip()
        ssl_val = (st_ssl or os.getenv("SMTP_SSL", "false")).lower()
        self.smtp_ssl = ssl_val in ("true", "1", "yes")

    def configure(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_pass: str,
        smtp_from: str = "",
        smtp_ssl: bool = False,
    ) -> None:
        """Dynamically set SMTP credentials at runtime."""
        self.smtp_host = smtp_host.strip()
        self.smtp_port = int(smtp_port)
        self.smtp_user = smtp_user.strip()
        self.smtp_pass = smtp_pass.replace(" ", "").strip() if "gmail" in smtp_host.lower() else smtp_pass.strip()
        self.smtp_from = (smtp_from or smtp_user or "no-reply@auraforest.gov.in").strip()
        self.smtp_ssl = smtp_ssl

    @property
    def is_configured(self) -> bool:
        """Return True if real SMTP server credentials are provided."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_pass)

    def test_connection(self) -> Dict[str, Any]:
        """Test live SMTP connection and authentication."""
        self.reload_config()
        if not self.is_configured:
            return {
                "success": False,
                "message": f"SMTP not configured (Host: {self.smtp_host}, User: '{self.smtp_user}', Pass: {'[SET]' if self.smtp_pass else '[EMPTY]'}). Please check Streamlit Secrets.",
                "host": self.smtp_host,
                "port": self.smtp_port,
                "user": self.smtp_user,
            }
        try:
            if self.smtp_ssl or self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                    server.login(self.smtp_user, self.smtp_pass)
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
            return {
                "success": True,
                "message": f"✅ SMTP Connection & Authentication Successful ({self.smtp_host}:{self.smtp_port} as {self.smtp_user})!",
                "host": self.smtp_host,
                "port": self.smtp_port,
                "user": self.smtp_user,
            }
        except Exception as exc:
            return {
                "success": False,
                "message": f"❌ SMTP Authentication Failed: {exc}",
                "host": self.smtp_host,
                "port": self.smtp_port,
                "user": self.smtp_user,
            }

    def send_otp_email(self, recipient_email: str, otp_code: str, user_name: str = "Citizen Observer") -> Dict[str, Any]:
        """
        Send a 6-digit OTP verification email to the user's email address.
        """
        self.reload_config()
        recipient_email = recipient_email.strip().lower()
        subject = f"🔐 Your AuraForest Sentinel Verification Code: {otp_code}"

        # Plaintext version
        plain_body = f"""
Hello {user_name},

Your one-time email verification code for AuraForest Sentinel registration is: {otp_code}

This code is valid for 5 minutes. Please enter it in the sign-up form to activate your account.

If you did not request this verification code, please ignore this email.

— AuraForest Bio-Defense Command
Ministry of Environment & Forests
        """.strip()

        # Premium HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #060a0c;
      margin: 0;
      padding: 24px;
      color: #edf6f3;
    }}
    .email-container {{
      max-width: 540px;
      margin: 0 auto;
      background: #0c1417;
      border: 1px solid rgba(124, 240, 178, 0.3);
      border-radius: 16px;
      padding: 32px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }}
    .header {{
      text-align: center;
      padding-bottom: 20px;
      border-bottom: 1px solid rgba(32, 54, 62, 0.7);
    }}
    .brand {{
      font-size: 20px;
      font-weight: 800;
      color: #7cf0b2;
      letter-spacing: -0.02em;
    }}
    .tagline {{
      font-size: 11px;
      color: #829a97;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin-top: 4px;
    }}
    .content {{
      padding: 24px 0;
    }}
    .greeting {{
      font-size: 16px;
      font-weight: 600;
      color: #ffffff;
      margin-bottom: 12px;
    }}
    .text {{
      font-size: 14px;
      line-height: 1.6;
      color: #c4d7d3;
      margin-bottom: 20px;
    }}
    .otp-card {{
      background: #101c20;
      border: 1.5px solid #7cf0b2;
      border-radius: 12px;
      padding: 18px;
      text-align: center;
      margin: 24px 0;
      box-shadow: 0 0 25px rgba(124, 240, 178, 0.2);
    }}
    .otp-code {{
      font-family: 'Courier New', Courier, monospace;
      font-size: 34px;
      font-weight: 800;
      color: #7cf0b2;
      letter-spacing: 8px;
    }}
    .otp-expiry {{
      font-size: 11px;
      color: #829a97;
      margin-top: 6px;
    }}
    .footer {{
      border-top: 1px solid rgba(32, 54, 62, 0.7);
      padding-top: 18px;
      text-align: center;
      font-size: 11px;
      color: #526563;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <div class="brand">◈ AURAFOREST SENTINEL</div>
      <div class="tagline">Bioacoustic & Threat Intelligence Platform</div>
    </div>
    <div class="content">
      <div class="greeting">Hello {user_name},</div>
      <div class="text">
        You requested a verification code to register your citizen account on the <b>AuraForest Sentinel</b> network.
      </div>
      <div class="otp-card">
        <div style="font-size:10px; color:#829a97; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:4px;">VERIFICATION PASSCODE</div>
        <div class="otp-code">{otp_code}</div>
        <div class="otp-expiry">⏱️ Valid for 5 minutes · Single-use only</div>
      </div>
      <div class="text">
        Enter this 6-digit code in the registration portal to complete your account setup and access real-time eco-readings and threat reporting.
      </div>
    </div>
    <div class="footer">
      <div>AuraForest Cyber-Defense Command · Automated Mail Delivery</div>
      <div>If you did not make this request, no action is needed.</div>
    </div>
  </div>
</body>
</html>
        """.strip()

        # Construct MIME Message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"AuraForest Sentinel <{self.smtp_from}>"
        msg["To"] = recipient_email
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        now_iso = datetime.now(timezone.utc).isoformat()

        # Real SMTP Delivery if credentials provided
        if self.is_configured:
            try:
                if self.smtp_ssl or self.smtp_port == 465:
                    with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                        server.login(self.smtp_user, self.smtp_pass)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                        server.starttls()
                        server.login(self.smtp_user, self.smtp_pass)
                        server.send_message(msg)

                return {
                    "success": True,
                    "delivered": True,
                    "channel": "SMTP_RELAY",
                    "recipient": recipient_email,
                    "subject": subject,
                    "otp_code": otp_code,
                    "timestamp": now_iso,
                    "message": f"Verification code successfully sent to {recipient_email} via SMTP.",
                    "html_preview": html_body,
                }
            except Exception as exc:
                print(f"[!] SMTP Delivery Error to {recipient_email}: {exc}")
                return {
                    "success": False,
                    "delivered": False,
                    "channel": "SMTP_ERROR",
                    "recipient": recipient_email,
                    "subject": subject,
                    "otp_code": otp_code,
                    "timestamp": now_iso,
                    "error": str(exc),
                    "message": f"SMTP Error sending to {recipient_email}: {exc}",
                    "html_preview": html_body,
                }

        # Not configured
        return {
            "success": False,
            "delivered": False,
            "channel": "NOT_CONFIGURED",
            "recipient": recipient_email,
            "subject": subject,
            "otp_code": otp_code,
            "timestamp": now_iso,
            "message": "SMTP credentials not configured. Please add SMTP_USER & SMTP_PASS in Streamlit Cloud Secrets.",
            "html_preview": html_body,
        }

    def send_ranger_credentials_email(
        self,
        recipient_email: str,
        full_name: str,
        username: str,
        password: str,
        callsign: str = "ALPHA-1",
        rank: str = "Field Ranger",
        sector: str = "Sector 4 (Tiger Corridor)",
    ) -> Dict[str, Any]:
        """
        Send an official appointment and login credentials email to a newly commissioned Field Ranger.
        """
        recipient_email = recipient_email.strip().lower()
        subject = f"🛡️ Official Commission & Sentinel Access Credentials — Ranger {full_name}"

        plain_body = f"""
Official Appointment & Security Notice
=======================================
Dear {full_name},

You have been officially commissioned to the AuraForest Tactical Field Defense Network by Chief Ranger Command.

YOUR ACCESS CREDENTIALS:
-------------------------
• Assigned Username: {username}
• Secure Passcode:   {password}
• Callsign:          {callsign}
• Rank / Role:       {rank}
• Deployment Sector: {sector}

INSTRUCTIONS:
1. Log in to the AuraForest Sentinel Portal (http://localhost:8501)
2. Select 'Field Ranger' or enter your username & password.
3. Access your live Tactical Incident Response Console and GPS Radar.

CONFIDENTIAL: Do not share these credentials with unauthorized personnel.

— Chief Ranger Cyber-Defense Command
AuraForest Wildlife Reserve · Ministry of Environment & Forests
        """.strip()

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #060a0c;
      margin: 0;
      padding: 24px;
      color: #edf6f3;
    }}
    .email-container {{
      max-width: 580px;
      margin: 0 auto;
      background: #0c1417;
      border: 1.5px solid rgba(115, 217, 232, 0.4);
      border-radius: 16px;
      padding: 32px;
      box-shadow: 0 12px 35px rgba(0, 0, 0, 0.6);
    }}
    .header {{
      text-align: center;
      padding-bottom: 20px;
      border-bottom: 1px solid rgba(32, 54, 62, 0.7);
    }}
    .brand {{
      font-size: 20px;
      font-weight: 800;
      color: #73d9e8;
      letter-spacing: -0.02em;
    }}
    .tagline {{
      font-size: 11px;
      color: #829a97;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin-top: 4px;
    }}
    .content {{
      padding: 24px 0;
    }}
    .greeting {{
      font-size: 16px;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 12px;
    }}
    .text {{
      font-size: 14px;
      line-height: 1.6;
      color: #c4d7d3;
      margin-bottom: 20px;
    }}
    .credentials-card {{
      background: #101c20;
      border: 1.5px solid #73d9e8;
      border-radius: 14px;
      padding: 20px;
      margin: 20px 0;
      box-shadow: 0 0 25px rgba(115, 217, 232, 0.2);
    }}
    .card-title {{
      font-size: 11px;
      color: #73d9e8;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 14px;
      border-bottom: 1px solid rgba(32, 54, 62, 0.7);
      padding-bottom: 6px;
    }}
    .cred-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid rgba(32, 54, 62, 0.4);
      font-size: 13px;
    }}
    .cred-row:last-child {{
      border-bottom: none;
    }}
    .cred-label {{
      color: #829a97;
    }}
    .cred-val {{
      font-family: 'Courier New', Courier, monospace;
      font-weight: 700;
      color: #edf6f3;
    }}
    .highlight {{
      color: #7cf0b2 !important;
      font-size: 15px;
    }}
    .highlight-cyan {{
      color: #73d9e8 !important;
      font-size: 15px;
    }}
    .footer {{
      border-top: 1px solid rgba(32, 54, 62, 0.7);
      padding-top: 18px;
      text-align: center;
      font-size: 11px;
      color: #526563;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <div class="brand">◈ AURAFOREST TACTICAL DEFENSE COMMAND</div>
      <div class="tagline">Official Field Ranger Appointment & Sentinel Access</div>
    </div>
    <div class="content">
      <div class="greeting">Dear Ranger {full_name},</div>
      <div class="text">
        You have been officially commissioned to the <b>AuraForest Field Response Network</b> by Chief Ranger Sharma. Your tactical access credentials and deployment sector have been established below:
      </div>
      <div class="credentials-card">
        <div class="card-title">🛡️ Field Ranger Access Credentials</div>
        <div class="cred-row">
          <span class="cred-label">Assigned Username:</span>
          <span class="cred-val highlight-cyan">{username}</span>
        </div>
        <div class="cred-row">
          <span class="cred-label">Access Password:</span>
          <span class="cred-val highlight">{password}</span>
        </div>
        <div class="cred-row">
          <span class="cred-label">Callsign / Unit:</span>
          <span class="cred-val">{callsign}</span>
        </div>
        <div class="cred-row">
          <span class="cred-label">Designation / Rank:</span>
          <span class="cred-val">{rank}</span>
        </div>
        <div class="cred-row">
          <span class="cred-label">Deployment Sector:</span>
          <span class="cred-val">{sector}</span>
        </div>
      </div>
      <div class="text">
        <b>Deployment Instructions:</b><br/>
        1. Access the Sentinel Operations Portal from your patrol terminal or mobile phone.<br/>
        2. Enter your assigned username and password.<br/>
        3. Review active acoustic AI threat alerts and GPS navigation to coordinate with nearby patrol buddies.
      </div>
    </div>
    <div class="footer">
      <div>CONFIDENTIAL & PROPRIETARY · Forestry Cyber-Defense Network</div>
      <div>Authorized by Chief Ranger Sharma · Ministry of Environment & Forests</div>
    </div>
  </div>
</body>
</html>
        """.strip()

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Chief Ranger Command <{self.smtp_from}>"
        msg["To"] = recipient_email
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        now_iso = datetime.now(timezone.utc).isoformat()

        if self.is_configured:
            try:
                if self.smtp_ssl or self.smtp_port == 465:
                    with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                        server.login(self.smtp_user, self.smtp_pass)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                        server.starttls()
                        server.login(self.smtp_user, self.smtp_pass)
                        server.send_message(msg)

                return {
                    "success": True,
                    "delivered": True,
                    "channel": "SMTP_RELAY",
                    "recipient": recipient_email,
                    "subject": subject,
                    "username": username,
                    "password": password,
                    "timestamp": now_iso,
                    "message": f"Appointment & credentials email sent to {recipient_email} via SMTP.",
                    "html_preview": html_body,
                }
            except Exception as exc:
                print(f"[!] SMTP Ranger Credentials Error to {recipient_email}: {exc}")
                return {
                    "success": False,
                    "delivered": False,
                    "channel": "SMTP_ERROR",
                    "recipient": recipient_email,
                    "subject": subject,
                    "username": username,
                    "password": password,
                    "timestamp": now_iso,
                    "error": str(exc),
                    "message": f"SMTP delivery failed to {recipient_email}: {exc}",
                    "html_preview": html_body,
                }

        return {
            "success": False,
            "delivered": False,
            "channel": "NOT_CONFIGURED",
            "recipient": recipient_email,
            "subject": subject,
            "username": username,
            "password": password,
            "timestamp": now_iso,
            "message": "SMTP credentials not configured in Streamlit Cloud Secrets.",
            "html_preview": html_body,
        }


    def send_chief_credentials_email(
        self,
        recipient_email: str,
        full_name: str = "Chief Ranger Sharma",
        username: str = "chief",
        password: str = "auraadmin123",
        callsign: str = "COMMAND-0",
        sector: str = "AuraForest Central Command HQ",
    ) -> Dict[str, Any]:
        """
        Send an official master administrator credentials email to the Chief Ranger.
        """
        recipient_email = recipient_email.strip().lower()
        subject = f"👑 AuraForest Sentinel Master Administrator Credentials — Chief Ranger Command"

        plain_body = f"""
AuraForest Sentinel — Chief Ranger Master Command Credentials
============================================================
Dear {full_name},

Below are your Master Administrator access credentials for the AuraForest Sentinel Defense & AI Telemetry System.

YOUR MASTER ACCESS CREDENTIALS:
-------------------------------
• User ID / Username: {username}
• Master Password:    {password}
• Callsign:           {callsign}
• Security Role:      Master Administrator (Chief Ranger)
• Command Sector:     {sector}

PORTAL ACCESS:
• Local Console URL:  http://localhost:8501

ADMIN PRIVILEGES:
1. Full Real-Time IoT & AI Telemetry Surveillance
2. Tactical Ranger Dispatch & Alert Resolution
3. Field Ranger Account Creation & Password Management
4. Citizen Report Review & Investigation Dispatch
5. AI Behavioral Model Adaptation & Spectrum Analysis

CONFIDENTIAL: These master administrative credentials grant unrestricted access to the entire forest defense grid. Keep them secure.

— AuraForest Cyber-Defense Operations
Ministry of Environment, Forest and Climate Change
        """.strip()

        now_iso = datetime.now(timezone.utc).isoformat()

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #05080a;
      margin: 0;
      padding: 24px;
      color: #edf6f3;
    }}
    .email-container {{
      max-width: 580px;
      margin: 0 auto;
      background: #0b1216;
      border: 1.5px solid #f6c445;
      border-radius: 16px;
      padding: 32px;
      box-shadow: 0 12px 40px rgba(246, 196, 69, 0.18);
    }}
    .header {{
      text-align: center;
      padding-bottom: 20px;
      border-bottom: 1px solid rgba(246, 196, 69, 0.3);
    }}
    .brand {{
      font-size: 20px;
      font-weight: 800;
      color: #f6c445;
      letter-spacing: -0.02em;
    }}
    .tagline {{
      font-size: 11px;
      color: #829a97;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin-top: 4px;
    }}
    .content {{
      padding: 24px 0;
    }}
    .greeting {{
      font-size: 16px;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 12px;
    }}
    .text {{
      font-size: 14px;
      line-height: 1.6;
      color: #c4d7d3;
      margin-bottom: 20px;
    }}
    .credentials-card {{
      background: #0e181d;
      border: 1.5px solid #f6c445;
      border-radius: 14px;
      padding: 22px;
      margin: 20px 0;
      box-shadow: 0 0 25px rgba(246, 196, 69, 0.15);
    }}
    .card-title {{
      font-size: 11px;
      color: #f6c445;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 14px;
      border-bottom: 1px solid rgba(246, 196, 69, 0.3);
      padding-bottom: 6px;
    }}
    .cred-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid rgba(32, 54, 62, 0.4);
      font-size: 13px;
    }}
    .cred-row:last-child {{
      border-bottom: none;
    }}
    .cred-label {{
      color: #829a97;
    }}
    .cred-val {{
      font-family: 'Courier New', Courier, monospace;
      font-weight: 700;
      color: #edf6f3;
    }}
    .highlight-gold {{
      color: #f6c445 !important;
      font-size: 16px;
    }}
    .highlight-cyan {{
      color: #73d9e8 !important;
      font-size: 16px;
    }}
    .footer {{
      border-top: 1px solid rgba(32, 54, 62, 0.7);
      padding-top: 18px;
      text-align: center;
      font-size: 11px;
      color: #526563;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <div class="brand">👑 AURAFOREST CENTRAL COMMAND</div>
      <div class="tagline">Master Administrator Credentials & Security Clearance</div>
    </div>
    <div class="content">
      <div class="greeting">Dear {full_name},</div>
      <div class="text">
        Below are your official master administrator credentials for the <b>AuraForest Sentinel Defense Network</b>:
      </div>
      <div class="credentials-card">
        <div class="card-title">👑 Chief Ranger Master Credentials</div>
        <div class="cred-row">
          <span class="cred-label">User ID / Username:</span>
          <span class="cred-val highlight-cyan">{username}</span>
        </div>
        <div class="cred-row">
          <span class="cred-label">Master Password:</span>
          <span class="cred-val highlight-gold">{password}</span>
        </div>
        <div class="cred-row">
          <span class="cred-label">Callsign:</span>
          <span class="cred-val">{callsign}</span>
        </div>
        <div class="cred-row">
          <span class="cred-label">Clearance Level:</span>
          <span class="cred-val" style="color:#7cf0b2;">Level 5 (Full Command Admin)</span>
        </div>
        <div class="cred-row">
          <span class="cred-label">HQ Sector:</span>
          <span class="cred-val">{sector}</span>
        </div>
      </div>
      <div class="text" style="font-size:12px; color:#829a97;">
        <b>Next Steps:</b> Log in to the Sentinel portal at <a href="http://localhost:8501" style="color:#73d9e8;">http://localhost:8501</a> using the credentials above to command field units, configure nodes, and inspect alerts.
      </div>
    </div>
    <div class="footer">
      <div>AuraForest Sentinel Cyber-Defense System · Ministry of Environment & Forests</div>
      <div style="margin-top:4px; font-size:10px;">Security Hash: AF-CMD-MASTER-AUTH</div>
    </div>
  </div>
</body>
</html>
        """.strip()

        # Attempt SMTP delivery
        self.reload_config()
        if self.is_configured:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"AuraForest Sentinel <{self.smtp_from}>"
                msg["To"] = recipient_email
                msg.attach(MIMEText(plain_body, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))

                if self.smtp_ssl or self.smtp_port == 465:
                    with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                        server.login(self.smtp_user, self.smtp_pass)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                        server.starttls()
                        server.login(self.smtp_user, self.smtp_pass)
                        server.send_message(msg)

                return {
                    "success": True,
                    "delivered": True,
                    "channel": "SMTP_RELAY",
                    "recipient": recipient_email,
                    "subject": subject,
                    "username": username,
                    "password": password,
                    "timestamp": now_iso,
                    "message": f"Chief credentials email successfully sent to {recipient_email} via SMTP.",
                    "html_preview": html_body,
                }
            except Exception as exc:
                print(f"[!] SMTP Chief Credentials Error to {recipient_email}: {exc}")
                return {
                    "success": False,
                    "delivered": False,
                    "channel": "SMTP_ERROR",
                    "recipient": recipient_email,
                    "subject": subject,
                    "username": username,
                    "password": password,
                    "timestamp": now_iso,
                    "error": str(exc),
                    "message": f"Chief credentials email failed: {exc}",
                    "html_preview": html_body,
                }

        return {
            "success": False,
            "delivered": False,
            "channel": "NOT_CONFIGURED",
            "recipient": recipient_email,
            "subject": subject,
            "username": username,
            "password": password,
            "timestamp": now_iso,
            "message": "SMTP credentials not configured in Streamlit Cloud Secrets.",
            "html_preview": html_body,
        }


# Global singleton
email_service = EmailService()
