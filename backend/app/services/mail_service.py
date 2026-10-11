import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from flask import current_app

logger = logging.getLogger(__name__)

class MailService:
    """
    Mail Service for user registration mail verification.
    Supports both HTTP Mail APIs (Brevo / Resend over HTTPS port 443 - immune to cloud firewall port blocks)
    and standard Gmail SMTP (Port 465 SSL / 587 TLS).
    """

    @staticmethod
    def send_verification_email(user_email: str, verification_token: str) -> bool:
        """
        Sends registration email verification link and token.
        Prioritizes HTTP APIs (Port 443) on cloud environments, with standard SMTP fallback.
        """
        try:
            base_url = current_app.config.get('BASE_URL') or os.environ.get('RENDER_EXTERNAL_URL') or 'https://smartbus-ai-r4ay.onrender.com'
            verification_url = f"{base_url.rstrip('/')}/api/auth/verify-email?token={verification_token}"

            mail_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
            mail_user = current_app.config.get('MAIL_USERNAME', '')
            mail_pass = current_app.config.get('MAIL_PASSWORD', '')
            sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'smartbusai.noreply@gmail.com')
            sender_email = mail_user if (mail_user and '@' in mail_user) else sender

            brevo_key = current_app.config.get('BREVO_API_KEY') or os.environ.get('BREVO_API_KEY', '')
            resend_key = current_app.config.get('RESEND_API_KEY') or os.environ.get('RESEND_API_KEY', '')

            subject = "SmartBus AI - Verify Your Email Address"

            body_text = (
                f"Welcome to SmartBus AI!\n\n"
                f"Your 4-digit verification code is: {verification_token}\n\n"
                f"Please enter this code on the verification screen to activate your account.\n"
                f"Or click: {verification_url}\n"
            )

            body_html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; background-color: #0f172a; padding: 30px; color: #f8fafc;">
                <div style="max-width: 520px; margin: 0 auto; background: #1e293b; padding: 32px; border-radius: 16px; border: 1px solid #334155; text-align: center;">
                  <h2 style="color: #38bdf8; margin-top: 0;">SmartBus AI</h2>
                  <p style="color: #cbd5e1; font-size: 15px;">Thank you for registering! Please use your One-Time PIN below to verify your email address:</p>
                  <div style="margin: 28px 0; padding: 18px; background: rgba(56, 189, 248, 0.1); border: 1px dashed #38bdf8; border-radius: 12px;">
                    <span style="font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #38bdf8;">{verification_token}</span>
                  </div>
                  <p style="color: #94a3b8; font-size: 13px;">Enter this PIN on the verification screen to complete your sign in.</p>
                  <div style="margin: 24px 0;">
                    <a href="{verification_url}" style="background: linear-gradient(135deg, #f97316 0%, #10b981 100%); color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">Verify Account</a>
                  </div>
                  <p style="color: #64748b; font-size: 11px;">If you did not request this verification code, please ignore this email.</p>
                </div>
              </body>
            </html>
            """

            # 1. Try Brevo HTTP REST API (Port 443 - 100% works on Render Free)
            if brevo_key:
                try:
                    res = requests.post(
                        "https://api.brevo.com/v3/smtp/email",
                        headers={
                            "accept": "application/json",
                            "api-key": brevo_key,
                            "content-type": "application/json"
                        },
                        json={
                            "sender": {"name": "SmartBus AI", "email": sender_email},
                            "to": [{"email": user_email}],
                            "subject": subject,
                            "htmlContent": body_html,
                            "textContent": body_text
                        },
                        timeout=8
                    )
                    if res.status_code in (200, 201, 202):
                        logger.info(f"Verification email sent to {user_email} via Brevo API")
                        return True
                    else:
                        logger.warning(f"Brevo API error: {res.status_code} {res.text}")
                except Exception as e_brevo:
                    logger.warning(f"Brevo API call failed: {e_brevo}")

            # 2. Try Resend HTTP REST API (Port 443 - 100% works on Render Free)
            if resend_key:
                try:
                    res = requests.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {resend_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "from": f"SmartBus AI <onboarding@resend.dev>",
                            "to": [user_email],
                            "subject": subject,
                            "html": body_html,
                            "text": body_text
                        },
                        timeout=8
                    )
                    if res.status_code in (200, 201, 202):
                        logger.info(f"Verification email sent to {user_email} via Resend API")
                        return True
                    else:
                        logger.warning(f"Resend API error: {res.status_code} {res.text}")
                except Exception as e_resend:
                    logger.warning(f"Resend API call failed: {e_resend}")

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"SmartBus AI <{sender_email}>"
            msg['To'] = user_email
            msg['Reply-To'] = sender_email

            msg.attach(MIMEText(body_text, 'plain'))
            msg.attach(MIMEText(body_html, 'html'))

            server = None
            connection_error = None

            # First priority: Port 465 SSL (Direct SMTPS - immune to cloud provider 587 throttling)
            try:
                server = smtplib.SMTP_SSL(mail_server, 465, timeout=12)
                if mail_user and mail_pass:
                    server.login(mail_user, mail_pass)
                server.sendmail(sender_email, [user_email], msg.as_string())
                server.quit()
                logger.info(f"Verification email successfully sent to {user_email} via Port 465 SSL")
                return True
            except Exception as e_ssl:
                connection_error = e_ssl
                logger.warning(f"Port 465 SSL attempt failed ({e_ssl}). Trying Port 587 STARTTLS...")

            # Second priority fallback: Port 587 TLS
            try:
                server = smtplib.SMTP(mail_server, 587, timeout=12)
                server.starttls()
                if mail_user and mail_pass:
                    server.login(mail_user, mail_pass)
                server.sendmail(sender_email, [user_email], msg.as_string())
                server.quit()
                logger.info(f"Verification email successfully sent to {user_email} via Port 587 TLS")
                return True
            except Exception as e_tls:
                logger.error(f"Both Port 465 and Port 587 failed: SSL ({connection_error}) | TLS ({e_tls})")
                print(f"\n[SMTP ERROR] Could not deliver email to {user_email}: {e_tls}")
                return False
        except Exception as e:
            logger.error(f"Failed to send SMTP verification email to {user_email}: {str(e)}")
            print(f"\n[SMTP ERROR / FALLBACK LOG] Mail Verification Token for {user_email}: {verification_token}\n")
            return False
