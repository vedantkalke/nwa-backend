import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

print(f"Sending from: {config.SENDER_EMAIL}")
print(f"Sending to: {config.TEAM_EMAIL}")
print(f"Password length: {len(config.SENDER_PASSWORD)} characters")

try:
    print("\nConnecting to Gmail...")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    
    print("Logging in...")
    server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
    
    print("Sending test email...")
    msg = MIMEMultipart()
    msg['From'] = config.SENDER_EMAIL
    msg['To'] = config.SENDER_EMAIL
    msg['Subject'] = "NWA Backend - Test Email"
    msg.attach(MIMEText("This is a test email from your NWA backend.", 'plain'))
    
    result = server.sendmail(config.SENDER_EMAIL, config.SENDER_EMAIL, msg.as_string())
    server.quit()
    
    print(f"Result: {result}")
    print("✅ Email sent successfully - check your inbox!")

except smtplib.SMTPAuthenticationError:
    print("❌ Authentication failed - App Password is wrong")
except smtplib.SMTPException as e:
    print(f"❌ SMTP Error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")