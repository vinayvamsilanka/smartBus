import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from flask import current_app

logger = logging.getLogger(__name__)

class MailService:
    """
    SMTP Mail Service for user registration mail verification.
    Uses standard smtplib with HTML formatting and fallback dev-logging.
    """

    @staticmethod
    def send_verification_email(user_email: str, verification_token: str) -> bool:
        """
        Sends registration email verification link and token via SMTP.
        If SMTP server fails or default credentials are set, falls back to logging the verification details.
        """
        try:
            mail_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
            mail_port = current_app.config.get('MAIL_PORT', 587)
            mail_use_tls = current_app.config.get('MAIL_USE_TLS', True)
            mail_use_ssl = current_app.config.get('MAIL_USE_SSL', False)
            mail_user = current_app.config.get('MAIL_USERNAME', '')
            mail_pass = current_app.config.get('MAIL_PASSWORD', '')
            sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@smartbus.com')

            subject = "SmartBus AI - Verify Your Email Address"
            verification_url = f"http://localhost:5000/api/auth/verify-email?token={verification_token}"

            body_text = (
                f"Welcome to SmartBus AI!\n\n"
                f"Please verify your email using token: {verification_token}\n"
                f"Or click link: {verification_url}\n"
            )

            body_html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; background-color: #f4f6f8; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                  <h2 style="color: #4f46e5;">Welcome to SmartBus AI!</h2>
                  <p>Thank you for registering. Please verify your email address to activate your account.</p>
                  <p>Your verification code is: <b style="font-size: 18px; color: #4f46e5;">{verification_token}</b></p>
                  <div style="margin: 25px 0;">
                    <a href="{verification_url}" style="background-color: #4f46e5; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Verify Email</a>
                  </div>
                  <p style="color: #6b7280; font-size: 12px;">If you did not request this, please ignore this email.</p>
                </div>
              </body>
            </html>
            """

            # Determine authenticated sender address
            sender_email = mail_user if (mail_user and '@' in mail_user) else sender

            # Check if using template/dummy credentials in dev mode
            if not mail_user or 'your_email' in mail_user or not mail_pass or 'your_app_password' in mail_pass:
                logger.info(f"[SMTP SIMULATED MAIL] Verification email for {user_email} generated.")
                print(f"\n[SMTP SIMULATED MAIL] Verification Email to {user_email}")
                print(f"Token: {verification_token}")
                print(f"Link: {verification_url}\n")
                return True

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
