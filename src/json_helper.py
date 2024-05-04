
from json import JSONEncoder

class ComplexEncoder(JSONEncoder):
    def default(self, obj):
        # print(f'-> obj: {obj}')
        if hasattr(obj, 'to_json'):
            return obj.to_json()
        else:
            return JSONEncoder.default(self, obj)
