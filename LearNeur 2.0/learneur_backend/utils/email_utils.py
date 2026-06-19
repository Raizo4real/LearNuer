# .
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv # 1. استدعاء المكتبة

load_dotenv() # 2. تفعيل قراءة ملف الـ .env أوتوماتيكياً

# Configuration: In production, load these from a .env file
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_otp_email(receiver_email: str, otp_code: str):
    """
    Sends a 6-digit OTP to the parent's email for PIN recovery.
    """
    subject = "LearNeur - Parent PIN Recovery"
    
    # HTML Email Template
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; border: 1px solid #E0E5EC; border-radius: 10px; padding: 20px;">
            <h2 style="color: #4FD1C5;">LearNeur Security</h2>
            <p>You requested to reset your Parent Dashboard PIN.</p>
            <p>Your 6-digit verification code is:</p>
            <h1 style="background: #F7FAFC; padding: 15px; text-align: center; letter-spacing: 5px; border-radius: 8px;">{otp_code}</h1>
            <p><i>This code expires in 15 minutes. If you did not request this, please ignore this email.</i></p>
        </div>
      </body>
    </html>
    """

    # Assemble Email
    message = MIMEMultipart()
    message["From"] = SMTP_USERNAME
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(html_content, "html"))

    try:
        # Connect to SMTP server and send
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() # Secure the connection
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, receiver_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
