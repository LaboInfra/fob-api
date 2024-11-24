from smtplib import SMTP, SMTPRecipientsRefused
from email.mime.text import MIMEText

from fob_api import Config

config = Config()

def send_text_mail(receivers: str | list, subject: str, text: str):
    server = SMTP('maildev', 1025)
    message = MIMEText(text, 'plain')
    message['Subject'] = subject
    message['From'] = config.mail_sender
    message['To'] = receivers if isinstance(receivers, str) else ', '.join(receivers)

    if config.mail_starttls:
        server.starttls()
    if config.mail_password:
        server.login(config.mail_username, config.mail_password)

    server.sendmail(config.mail_sender, receivers, message.as_string())
    server.quit()
