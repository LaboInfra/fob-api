from os import environ

def parse_bool(value: str) -> bool:
    """
    Parse a string to a boolean value
    :param value: The value to parse
    :return: The boolean value or None if the value is not recognized
    """
    if not value:
        return None
    list_of_true = ["true", "yes", "1"]
    list_of_false = ["false", "no", "0"]
    if value.lower() in list_of_true:
        return True
    if value.lower() in list_of_false:
        return False

class SingletonMeta(type):

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class Config(metaclass=SingletonMeta):

    database_url: str
    
    firezone_endpoint: str
    firezone_token: str

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

    def __init__(self):
        print("Initializing Config Singleton")

        if not environ.get("DISABLE_DOTENV", False):
            print("Loading .env file into environment (You can disable this by setting DISABLE_DOTENV=True)")
            from dotenv import load_dotenv
            load_dotenv()

        self.database_url = environ.get("DATABASE_URL")

        self.firezone_endpoint = environ.get("FIREZONE_ENDPOINT")
        self.firezone_token = environ.get("FIREZONE_TOKEN")

        self.celery_broker_url = environ.get("CELERY_BROKER_URL")
        self.celery_result_backend = environ.get("CELERY_RESULT_BACKEND")

        self.jwt_secret_key = environ.get("SECRET_KEY")

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

        ignore = ["MAIL_PASSWORD"]

        not_set = [
            key.upper()
            for key, value in self.__dict__.items()
            if value == None and key.upper() not in ignore
        ]

        if not_set:
            raise ValueError(f"Environment variables not set: {', '.join(not_set)}")
        print("Config Singleton initialized")
