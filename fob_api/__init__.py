from dotenv import load_dotenv

from .database import init_engine


load_dotenv()
engine = init_engine()
