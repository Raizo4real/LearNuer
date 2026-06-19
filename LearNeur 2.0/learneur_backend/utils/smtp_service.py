import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
# --- إعدادات سيرفر الـ SMTP ---
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SMTP_USERNAME")
SENDER_PASSWORD = os.getenv("SMTP_PASSWORD")   

# --- القالب الموحد للإيميلات (HTML Template) ---
def get_email_template(title: str, content_html: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f9f9; margin: 0; padding: 0; direction: ltr; }}
            .container {{ max-width: 600px; margin: 30px auto; background: #ffffff; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid rgba(79, 209, 197, 0.2); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #203A43 0%, #2C5364 100%); padding: 30px; text-align: center; }}
            .logo {{ font-size: 28px; font-weight: bold; color: #4FD1C5; letter-spacing: 1px; margin: 0; }}
            .content {{ padding: 40px 30px; color: #2D3748; line-height: 1.6; }}
            .title {{ font-size: 22px; font-weight: 700; color: #2D3748; margin-bottom: 20px; }}
            .footer {{ background-color: #f7fafc; padding: 20px; text-align: center; font-size: 12px; color: #A0AEC0; border-top: 1px solid #edf2f7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">LearNeur</div>
            </div>
            <div class="content">
                <div class="title">{title}</div>
                {content_html}
            </div>
            <div class="footer">
                This is an automated security notification from LearNeur.<br>
                &copy; 2026 LearNeur Platform. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

async def send_otp_email(to_email: str, otp_code: str, action: str):
    subject = f"LearNeur Security - Verification Code for {action.capitalize()}"
    
    # تصميم جزء الـ OTP بشكل شيك جداً (كارت مبهج وواضح)
    content_html = f"""
    <p>Hello,</p>
    <p>We received a request to perform a secure action: <strong>{action}</strong> on your LearNeur account.</p>
    <p>Please use the verification code below to complete the process. This code is valid for a limited time.</p>
    
    <div style="background: #edf2f7; border-radius: 16px; padding: 20px; text-align: center; margin: 30px 0; border: 2px dashed #4FD1C5;">
        <span style="font-size: 32px; font-weight: 800; color: #2C5364; letter-spacing: 8px; font-family: monospace;">{otp_code}</span>
    </div>
    
    <p style="color: #E53E3E; font-size: 14px; font-weight: 600;">⚠️ Security Notice: Do NOT share this code with anyone, including LearNeur support staff.</p>
    """
    
    full_html = get_email_template(f"Your OTP Verification Code", content_html)
    
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(full_html, 'html', 'utf-8')) # 👈 قلبنا النوع لـ html هنا
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"🎉 SUCCESS: Beautiful HTML OTP sent to {to_email}")
    except Exception as e:
        print(f"❌ SMTP ERROR: {e}")

async def send_email_changed_alerts(old_email: str, new_email: str, parent_name: str, masked_new_email: str):
    # 1. إرسال تنبيه حماية للإيميل القديم
    old_subject = "LearNeur Security Alert: Email Changed"
    old_html = f"""
    <p>Hello {parent_name},</p>
    <p>Your LearNeur account email address was successfully updated to: <strong style="color: #4FD1C5;">{masked_new_email}</strong>.</p>
    <p>If you authorized this change, you can safely ignore this message.</p>
    
    <div style="background: #FFF5F5; border-left: 4px solid #E53E3E; border-radius: 8px; padding: 15px; margin: 25px 0; color: #C53030;">
        <strong>Did not authorize this change?</strong><br>
        If this was not you, please contact our security team immediately to secure your account.
    </div>
    """
    
    # 2. إرسال ترحيب للإيميل الجديد
    new_subject = "LearNeur: Email Successfully Linked"
    new_html = f"""
    <p>Hello {parent_name},</p>
    <p>Welcome to your new primary inbox! This email address is now successfully linked to your LearNeur profile.</p>
    <p>From now on, all security codes, updates, and child telemetry reports will be delivered here.</p>
    """
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # إرسال للقديم
        msg_old = MIMEMultipart()
        msg_old['From'] = SENDER_EMAIL
        msg_old['To'] = old_email
        msg_old['Subject'] = old_subject
        msg_old.attach(MIMEText(get_email_template("Security Notification", old_html), 'html', 'utf-8'))
        server.send_message(msg_old)
        
        # إرسال للجديد
        msg_new = MIMEMultipart()
        msg_new['From'] = SENDER_EMAIL
        msg_new['To'] = new_email
        msg_new['Subject'] = new_subject
        msg_new.attach(MIMEText(get_email_template("Email Update Successful", new_html), 'html', 'utf-8'))
        server.send_message(msg_new)
        
        server.quit()
        print(f"🎉 SUCCESS: Beautiful HTML Security alerts sent successfully.")
    except Exception as e:
        print(f"❌ SMTP ERROR during email change alerts: {e}")

# File: utils/smtp_service.py
# Make sure to import your actual email sending libraries (e.g., smtplib, email.mime)

async def send_verification_email(to_email: str, token: str):
    # Determine your base URL (Use env variables in production)
    BASE_URL = "http://127.0.0.1:8000" 
    verification_link = f"{BASE_URL}/auth/verify-email?token={token}"

    subject = "Welcome to LearNeur! Verify your account"
    
    # Premium HTML Email Template
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Nunito', sans-serif; background-color: #EBF8FF; padding: 40px 0; margin: 0; text-align: center;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
            <h1 style="color: #4FD1C5; margin-bottom: 10px;">LearNeur</h1>
            <h2 style="color: #2D3748;">Verify Your Email Address</h2>
            <p style="color: #718096; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                Welcome to the LearNeur community! We are thrilled to have you. Please verify your email address to activate your Parent Dashboard and secure your child's playroom.
            </p>
            <a href="{verification_link}" style="display: inline-block; background-color: #4FD1C5; color: #ffffff; text-decoration: none; font-size: 18px; font-weight: bold; padding: 15px 30px; border-radius: 30px; box-shadow: 0 4px 15px rgba(79, 209, 197, 0.4);">
                Verify My Account
            </a>
            <p style="color: #A0AEC0; font-size: 12px; margin-top: 30px;">
                If you did not create this account, you can safely ignore this email.<br>
                This link will expire in 24 hours.
            </p>
        </div>
    </body>
    </html>
    """
    
    # تجهيز الرسالة
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # إرسال الرسالة فعلياً عبر سيرفر الجيميل
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"🎉 SUCCESS: Magic Link sent to {to_email}")
    except Exception as e:
        print(f"❌ SMTP ERROR: Failed to send verification email: {e}")
