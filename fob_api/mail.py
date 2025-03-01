from smtplib import SMTP
from ssl import _create_unverified_context
from email.mime.text import MIMEText

from jinja2 import Environment, FileSystemLoader

from fob_api import Config

config = Config()

# Ignore SSL certificate errors
context = _create_unverified_context()

jinja_engine = Environment(loader=FileSystemLoader('templates/mail'), autoescape=True)

template_data_base = {
    "site_url": "https://docs.laboinfra.net",
    "site_name": "LaboInfra",
    "support_email": "contact@laboinfra.net",
}

def send_mail(receivers: str | list, subject: str, template: str, template_data: dict):
    """
        Send an email using the given template and data
    """
    server = SMTP(config.mail_server, config.mail_port)
    message = MIMEText(jinja_engine.get_template(template).render({**template_data_base, **template_data}), 'html')
    message['Subject'] = subject
    message['From'] = config.mail_sender
    message['To'] = receivers if isinstance(receivers, str) else ', '.join(receivers)

    if config.mail_starttls:
        server.starttls(context=context)
    if config.mail_password:
        server.login(config.mail_username, config.mail_password)

    server.sendmail(config.mail_sender, receivers, message.as_string())
    server.quit()
