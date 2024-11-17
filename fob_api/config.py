from os import environ

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

        not_set = [
            key.upper()
            for key, value in self.__dict__.items()
            if not value
        ]
    
        if not_set:
            raise ValueError(f"Environment variables not set: {', '.join(not_set)}")
        print("Config Singleton initialized")