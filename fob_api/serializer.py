from json import JSONEncoder, dumps, loads
from pydantic import BaseModel
from fob_api.models import api as api_models

class PydanticSerializer(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump() | {'__type__': type(obj).__name__}
        else:
            return JSONEncoder.default(self, obj)

def pydantic_decoder(obj):
    if '__type__' in obj and obj['__type__'] in dir(api_models):
        cls = getattr(api_models, obj['__type__'])
        return cls.parse_obj(obj)
    return obj


# Encoder function
def pydantic_dumps(obj):
    return dumps(obj, cls=PydanticSerializer)

# Decoder function
def pydantic_loads(obj):
    return loads(obj, object_hook=pydantic_decoder)
