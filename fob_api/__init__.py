from fastapi.security import HTTPBasic

from dotenv import load_dotenv

from .database import init_engine

# load the environment variables from the .env file
load_dotenv()

# initialize the database engine
engine = init_engine()

# initialize the security object
security = HTTPBasic()
