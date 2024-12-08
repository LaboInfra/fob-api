import requests

class BaseModel:

    __path__ = ""
    __driver__ = None

    def __init__(self, **kwargs):
        if '__driver__' in kwargs:
            self.__driver__ = kwargs['__driver__']
            del kwargs['__driver__']
        self.__path__ = f'{self.__driver__.server_url}{self.__path__}'
        self.__dict__.update(kwargs)

    def list(self):
        raise NotImplementedError

    def find(self, **kwargs):
        raise NotImplementedError
    
    def get(self, **kwargs):
        raise NotImplementedError
    
    def create(self, **kwargs):
        raise NotImplementedError
    
    def update(self, **kwargs):
        raise NotImplementedError
    
    def delete(self, **kwargs):
        raise NotImplementedError

class User(BaseModel):
    
    __path__ = '/api/v1/user'
    
    id: str
    name: str
    created_at: str

    def list(self) -> list['User']:
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

class Node(BaseModel):

    __path__ = '/api/v1/node'

    def register(self, name: str, mkey: str):
        server_reply = requests.post(f'{self.__path__}/register?user={name}&key={mkey}', headers=self.__driver__.headers)
        if server_reply.status_code != 200:
            raise Exception(f'Error: {server_reply.status_code} - {server_reply.text}')
        return server_reply.json()

class HeadScale:

    user: User
    node: Node

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
        self.node = Node(__driver__=self)
