from os import environ

def parse_bool(value: str) -> bool:
    """
    Parse a string to a boolean value
    :param value: The value to parse
    :return: The boolean value or None if the value is not recognized
    """
    list_of_true = ["true", "yes", "1"]
    list_of_false = ["false", "no", "0"]
    if value.lower() in list_of_true:
        return True
    if value.lower() in list_of_false:
        return False
    raise ValueError(f"Value {value} is not recognized as a boolean use one of {list_of_true + list_of_false}")

class SingletonMeta(type):

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class Config(metaclass=SingletonMeta):

    database_url: str

    headscale_endpoint: str
    headscale_token: str

    celery_broker_url: str
    celery_result_backend: str

    jwt_secret_key: str

    mail_server: str
    mail_port: int
    mail_username: str
    mail_password: str
    mail_starttls: bool
    mail_sender: str

    os_username: str
    os_password: str
    os_project_name: str
    os_user_domain_name: str
    os_project_domain_name: str
    os_auth_url: str

    openstack_domain_id: str
    openstack_role_member_id: str

    def __init__(self):
        print("Initializing Config Singleton")

        if not environ.get("DISABLE_DOTENV", False):
            print("Loading .env file into environment (You can disable this by setting DISABLE_DOTENV=True)")
            from dotenv import load_dotenv
            load_dotenv()

        self.database_url = environ.get("DATABASE_URL")
        self.headscale_endpoint = environ.get("HEADSCALE_ENDPOINT")
        self.headscale_token = environ.get("HEADSCALE_TOKEN")
        self.celery_broker_url = environ.get("CELERY_BROKER_URL")
        self.celery_result_backend = environ.get("CELERY_RESULT_BACKEND")

        self.jwt_secret_key = environ.get("JWT_SECRET_KEY")

        self.mail_server = environ.get("MAIL_SERVER")
        self.mail_port = int(environ.get("MAIL_PORT"))
        self.mail_username = environ.get("MAIL_USERNAME")
        self.mail_password = environ.get("MAIL_PASSWORD")
        self.mail_starttls = parse_bool(environ.get("MAIL_STARTTLS"))
        self.mail_sender = environ.get("MAIL_SENDER") or self.mail_username

        self.os_username = environ.get("OS_USERNAME")
        self.os_password = environ.get("OS_PASSWORD")
        self.os_project_name = environ.get("OS_PROJECT_NAME")
        self.os_user_domain_name = environ.get("OS_USER_DOMAIN_NAME")
        self.os_project_domain_name = environ.get("OS_PROJECT_DOMAIN_NAME")
        self.os_auth_url = environ.get("OS_AUTH_URL")

        self.openstack_domain_id = environ.get("OPENSTACK_DOMAIN_ID")
        self.openstack_role_member_id = environ.get("OPENSTACK_ROLE_MEMBER_ID")

        ignore = ["MAIL_PASSWORD"]

        not_set = [
            key.upper()
            for key, value in self.__dict__.items()
            if value == None and key.upper() not in ignore
        ]

        if not_set:
            raise ValueError(f"Environment variables not set: {', '.join(not_set)}")
        print("Config Singleton initialized")

    def validate_openstack_credentials(self) -> bool:
        """
        Validate the OpenStack credentials
        :return: True if the credentials are valid, False otherwise
        """
        from fob_api.managers import OpenStackManager
        osm = OpenStackManager()
        try:
            osm.get_keystone_client().endpoints.list()
            print("OpenStack credentials are valid")
            return True
        except Exception as e:
            print(f"Error validating OpenStack credentials: {e}")
            return False
    
    def validate_headscale_credentials(self) -> bool:
        """
        Validate the Headscale credentials
        :return: True if the credentials are valid, False otherwise
        """
        from fob_api import headscale_driver
        try:
            headscale_driver.user.list()
            print("Headscale credentials are valid")
            return True
        except Exception as e:
            print(f"Error validating Headscale credentials: {e}")
            return False

    def validate_email(self) -> bool:
        """
        Validate the email credentials
        :return: True if the credentials are valid, False otherwise
        """
        from fob_api import mail
        try:
            mail.send_text_mail(
                subject="Test email sending credentials validation",
                receivers=[self.mail_sender],
                body="This is a test email",
            )
            print("Email credentials are valid")
            return True
        except Exception as e:
            print(f"Error validating email credentials: {e}")
            return False
    
    def validate_all(self) -> bool:
        """
        Validate all credentials
        :return: True if all credentials are valid, False otherwise
        """
        print("Validating all credentials")
        return (
            self.validate_openstack_credentials() and
            self.validate_headscale_credentials() and
            self.validate_email()
        )
