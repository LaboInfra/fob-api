from jose import jwt
from jose.jwt import JWTClaimsError, JWTError, ExpiredSignatureError

from uuid import uuid4
from datetime import datetime, timedelta
import time

secret = "secret"
algorithm = "HS256"

payload = {
    'iss': 'FastOnBoard-API',
    'uuid': str(uuid4()),
    'exp': datetime.now() + timedelta(seconds=10),
    'iat': datetime.now(),
    'nbf': datetime.now(),
}

token = jwt.encode(payload, secret, algorithm=algorithm)

try:
    claims = jwt.decode(token, secret, algorithms=[algorithm], issuer='FastOnBoard-API')
    print(claims)
except JWTClaimsError as e:
    print(f'JWTClaimsError: {e}')

time.sleep(11)

try:
    claims = jwt.decode(token, secret, algorithms=[algorithm], issuer='FastOnBoard-API')
    print(claims)
except ExpiredSignatureError as e:
    print(f'ExpiredSignatureError: {e}')
except JWTClaimsError as e:
    print(f'JWTClaimsError: {e}')
except JWTError as e:
    print(f'JWTError: {e}')
