import pandas as pd
import smtplib
import time
import os
import json
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === LOAD .env CREDENTIALS ===
load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")

# === CONFIGURATION ===
CSV_FILE = "Directory.csv"
LOG_FILE = "sent_log.json"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
DAILY_LIMIT = 200
DELAY_SECONDS = 10

# === LOAD PREVIOUSLY SENT EMAILS ===
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'r') as f:
        sent_log = json.load(f)
else:
    sent_log = {}

# === LOAD CONTACTS ===
df = pd.read_csv(CSV_FILE)
df = df.drop_duplicates(subset=['School Email Address'])
df = df[df['School Email Address'].notna()]
df = df[~df['School Email Address'].isin(sent_log.keys())]

# === CONNECT TO SMTP ===
server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
server.starttls()
server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

sent_count = 0

for index, row in df.iterrows():
    if sent_count >= DAILY_LIMIT:
        break

    to_email = row['School Email Address']
    principal = row['School Principal'] if pd.notna(row['School Principal']) else "Principal"
    district = row['District Name']

    subject = f"HallHop – Digital Hall Pass for {district}"
    body = f"""Dear {principal},

I hope this message finds you well. I'm reaching out to introduce HallHop — a student-led, privacy-conscious digital hall pass system designed to help schools like those in {district} modernize hallway management without requiring expensive infrastructure.

HallHop helps staff track hallway activity in real time, reduce classroom disruptions, and increase student accountability — all with minimal setup and full transparency.

To learn more or request access, visit https://hallhop.com or reply directly to this message. We'd love to support your campus.

Thank you for your time and for all that you do.

Best regards,  
Varun Bhadurgatte Nagaraj  
512-212-6269  
HallHop Founder & CEO  
Junior at Round Rock High School  
hallhop.com – making hallways safer and smarter
"""

    # === COMPOSE EMAIL ===
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.add_header("Reply-To", EMAIL_ADDRESS)
    msg.add_header("X-Priority", "3")
    msg.add_header("X-Mailer", "Python smtplib")
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        print(f"✅ Sent to {to_email}")
        sent_log[to_email] = {
            "principal": principal,
            "district": district,
            "subject": subject,
            "body": body
        }
        sent_count += 1
        time.sleep(DELAY_SECONDS)
    except smtplib.SMTPException as e:
        print(f"⚠️ Error sending to {to_email}: {e}")

# === CLOSE CONNECTION & SAVE LOG ===
server.quit()
with open(LOG_FILE, 'w') as f:
    json.dump(sent_log, f, indent=2)

print(f"\n🎉 Finished. {sent_count} emails sent and logged.")