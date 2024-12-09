from datetime import datetime
from typing import List
import json
import requests

DATE_FORMAT_STRPTIME = "%Y-%m-%dT%H:%M:%S.%fZ"

def parse_datetime(date_str: str) -> datetime:
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

class DataModel:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class BaseModel(DataModel):

    __path__ = ""
    __driver__ = None

    def __init__(self, **kwargs):
        if '__driver__' in kwargs:
            self.__driver__ = kwargs['__driver__']
            del kwargs['__driver__']
        self.__path__ = f'{self.__driver__.server_url}{self.__path__}'
        super().__init__(**kwargs)

class User(BaseModel):
    
    __path__ = '/api/v1/user'
    
    id: str
    name: str
    created_at: str

    def list(self) -> List['User']:
        server_reply = requests.get(f'{self.__path__}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return [User(__driver__=self.__driver__, **user) for user in server_reply.json().get('users', [])]

    def create(self, name: str) -> 'User':
        server_reply = requests.post(f'{self.__path__}', headers=self.__driver__.headers, json={'name': name})
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return User(__driver__=self.__driver__, **server_reply.json())

    def get(self, name: str) -> 'User':
        server_reply = requests.get(f'{self.__path__}/{name}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return User(__driver__=self.__driver__, **server_reply.json())

    def rename(self, name: str, new_name: str) -> 'User':
        server_reply = requests.post(f'{self.__path__}/{name}/rename/{new_name}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return User(__driver__=self.__driver__, **server_reply.json())

    def delete(self, name: str):
        server_reply = requests.delete(f'{self.__path__}/{name}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return server_reply.json()

class PreAuthKey(BaseModel):

    __path__ = '/api/v1/preauthkey'

    user: str
    id: str
    key: str
    reusable: bool
    ephemeral: bool
    used: bool
    expiration: str
    createdAt: str
    aclTags: List[str]

    def is_expired(self) -> bool:
        return parse_datetime(self.expiration) < parse_datetime(datetime.now().strftime(DATE_FORMAT_STRPTIME)) or self.used

    def list(self, username) -> List['PreAuthKey']:
        server_reply = requests.get(f'{self.__path__}?user={username}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return [PreAuthKey(__driver__=self.__driver__, **key) for key in server_reply.json().get('preAuthKeys', [])]

    def create(self,
               username: str, 
               expiration: datetime,
               reusable: bool = False,
               ephemeral: bool = False,
               aclTags: List[str] = []
        ) -> 'PreAuthKey':
        server_reply = requests.post(f'{self.__path__}', headers=self.__driver__.headers, json={
            'user': username,
            'reusable': reusable,
            'ephemeral': ephemeral,
            'expiration': expiration.strftime(DATE_FORMAT_STRPTIME),
            'aclTags': aclTags
        })
        print(server_reply.json())
    
    def expire(self, username: str, key_value: str) -> dict:
        server_reply = requests.post(f'{self.__path__}/expire', headers=self.__driver__.headers, json={'user': username, 'key': key_value})
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return server_reply.json()

class Node(BaseModel):

    __path__ = '/api/v1/node'

    id: str
    machineKey: str
    nodeKey: str
    discoKey: str
    ipAddresses: List[str]
    name: str
    user: User | dict
    lastSeen: str
    expiry: str
    preAuthKey: PreAuthKey | dict
    createdAt: str
    registerMethod: str
    forcedTags: List[str]
    invalidTags: List[str]
    validTags: List[str]
    givenName: str
    online: bool

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'user' in kwargs and isinstance(self.user, dict):
            self.user = User(__driver__=self.__driver__, **self.user)
        if 'preAuthKey' in kwargs and isinstance(self.preAuthKey, dict):
            self.preAuthKey = PreAuthKey(__driver__=self.__driver__, **self.preAuthKey)

    def list(self, username: str = "") -> List['Node']:
        path = f'{self.__path__}' + (f'?user={username}' if username else '')
        server_reply = requests.get(f'{path}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return [Node(__driver__=self.__driver__, **node) for node in server_reply.json().get('nodes', [])]

    def get(self, id: str) -> 'Node':
        server_reply = requests.get(f'{self.__path__}/{id}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return Node(__driver__=self.__driver__, **server_reply.json().get('node', {}))

    def delete(self, id: str) -> dict:
        server_reply = requests.delete(f'{self.__path__}/{id}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return server_reply.json()
    
    def register(self, name: str, mkey: str) -> 'Node':
        server_reply = requests.post(f'{self.__path__}/register?user={name}&key={mkey}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return Node(__driver__=self.__driver__, **server_reply.json().get('node', {}))
    
    def backfillips(self, confirmed: bool = False) -> List[str]:
        server_reply = requests.post(f'{self.__path__}/backfillips?confirmed={str(confirmed).lower()}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return server_reply.json().get("changes", [])
    
    def expire(self, id: str) -> 'Node':
        server_reply = requests.post(f'{self.__path__}/{id}/expire', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return Node(__driver__=self.__driver__, **server_reply.json().get('node', {}))

    def rename(self, id: str, new_name: str) -> 'Node':
        server_reply = requests.post(f'{self.__path__}/{id}/rename/{new_name}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return Node(__driver__=self.__driver__, **server_reply.json().get('node', {}))
    
    def get_route(self, id: str) -> dict:
        server_reply = requests.get(f'{self.__path__}/{id}/route', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return server_reply.json() # Todo Return json until we have a Route model

    def set_tags(self, id: str, tags: List[str]) -> 'Node':
        server_reply = requests.post(f'{self.__path__}/{id}/tags', headers=self.__driver__.headers, json={'tags': tags})
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return Node(__driver__=self.__driver__, **server_reply.json().get('node', {}))

    def change_owner(self, id: str, username: str) -> 'Node':
        server_reply = requests.post(f'{self.__path__}/{id}/user?user={username}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return Node(__driver__=self.__driver__, **server_reply.json().get('node', {}))

class Route(BaseModel):

    __path__ = '/api/v1/routes'

    id: str
    node: Node | dict
    prefix: str
    advertised: bool
    enabled: bool
    isPrimary: bool
    createdAt: str
    updatedAt: str
    deletedAt: str | None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'node' in kwargs and isinstance(kwargs['node'], dict):
            self.node = Node(__driver__=self.__driver__, **self.node)

    def list(self) -> List['Route']:
        server_reply = requests.get(f'{self.__path__}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return [Route(__driver__=self.__driver__, **route) for route in server_reply.json().get('routes', [])]

    def delete(self, router_id: str) -> dict:
        server_reply = requests.delete(f'{self.__path__}/{router_id}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return server_reply.json()

    def set_status(self, router_id: str, active: bool) -> dict:
        path = f'{self.__path__}/{router_id}/' + ('enable' if active else 'disable')
        server_reply = requests.post(f'{path}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return server_reply.json()

    def enable(self, router_id: str) -> dict:
        return self.set_status(router_id, True)
    
    def disable(self, router_id: str) -> dict:
        return self.set_status(router_id, False)

class PolicyACL(DataModel):
    action: str
    src: List[str]
    dst: List[str]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'src' in kwargs and not isinstance(kwargs['src'], list):
            self.src = kwargs['src'].split(',')
        if 'dst' in kwargs and not isinstance(kwargs['dst'], list):
            self.dst = kwargs['dst'].split(',')


class PolicyData(DataModel):
    
    acls: List[PolicyACL]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'acls' in kwargs:
            self.acls = [PolicyACL(**acl) for acl in kwargs['acls']]

class Policy(BaseModel):

    __path__ = '/api/v1/policy'

    policy: PolicyData | str
    updatedAt: str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # check if policy is a string and load jsondump
        if 'policy' in kwargs and isinstance(kwargs['policy'], str):
            self.policy = PolicyData(**json.loads(kwargs['policy']))

    def get(self) -> 'Policy':
        server_reply = requests.get(f'{self.__path__}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return Policy(__driver__=self.__driver__, **server_reply.json())

    def get_policy_data(self) -> 'PolicyData':
        return self.get().policy

    def dump(self, policy_data: PolicyData) -> dict:
        return json.dumps(policy_data.__dict__, default=lambda o: o.__dict__)
    
    def update(self, policy_data: PolicyData) -> 'Policy':
        server_reply = requests.put(
            f'{self.__path__}',
            headers=self.__driver__.headers,
            json={
                'policy': self.dump(policy_data)
            })
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return Policy(__driver__=self.__driver__, **server_reply.json())

class HeadScale:

    user: User
    preauthkey: PreAuthKey
    node: Node
    route: Route
    policy: Policy

    def __init__(self, server_url: str, api_key: str):
        # Remove trailing slash
        self.server_url = server_url
        if server_url[-1] == '/':
            self.server_url = server_url[:-1]

        self.api_key = api_key
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'fast_onboarding-api'
        }

        # Initialize models
        self.user = User(__driver__=self)
        self.preauthkey = PreAuthKey(__driver__=self)
        self.node = Node(__driver__=self)
        self.route = Route(__driver__=self)
        self.policy = Policy(__driver__=self)
