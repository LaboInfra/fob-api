from smtplib import SMTP, SMTPRecipientsRefused
from ssl import _create_unverified_context
from email.mime.text import MIMEText

from fob_api import Config

config = Config()

# Ignore SSL certificate errors
context = _create_unverified_context()

def send_text_mail(receivers: str | list, subject: str, text: str):
    server = SMTP(config.mail_server, config.mail_port)
    message = MIMEText(text, 'plain')
    message['Subject'] = subject
    message['From'] = config.mail_sender
    message['To'] = receivers if isinstance(receivers, str) else ', '.join(receivers)

    if config.mail_starttls:
        server.starttls(context=context)
    if config.mail_password:
        server.login(config.mail_username, config.mail_password)

    server.sendmail(config.mail_sender, receivers, message.as_string())
    server.quit()
