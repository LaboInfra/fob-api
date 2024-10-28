"""
this module is for getting token from file gen by the user or CI for running test
"""
from os.path import exists

api_endpoint = "http://localhost:13000/v0"

def get_token() -> str:
    """
    return token as string or raise a exception if file not exist
    """
    if not exists(".token"):
        raise Exception(".token file not found for test")
    with open(".token", 'r', encoding="UTF-8") as stream:
        return stream.readline()

if __name__ == "__main__":
    print(get_token())
