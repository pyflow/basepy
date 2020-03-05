import json

class ToDictMixin:
    @staticmethod
    def dump_obj(obj, depth=0, max_depth=1):
        if obj is None:
            return None
        elif isinstance(obj, bytes):
            try:
                return str(obj, 'utf-8')
            except:
                return obj
        elif isinstance(obj, (bool, int, float, str)):
            return obj
        elif isinstance(obj, (tuple, list)):
            return [ToDictMixin.dump_obj(x, depth=depth, max_depth=max_depth) for x in obj]
        elif isinstance(obj, dict):
            value_dict = {}
            for key, value in obj.items():
                value_dict[str(key)] = ToDictMixin.dump_obj(value, depth=depth, max_depth=max_depth)
            return value_dict

        if depth >= max_depth or not hasattr(obj, "__dict__"):
            return "<{} instance at {}>".format(type(obj).__name__, hex(id(obj)))

        dump_dict = {}

        for key, value in vars(obj).items():
            if hasattr(value, 'to_dict'):
                dump_dict[key] = value.to_dict()
            else:
                dump_dict[key] = ToDictMixin.dump_obj(value, depth=depth+1, max_depth=max_depth)
        return dump_dict

    def to_dict(self):
        if not hasattr(self, "__dict__"):
            return {}
        return ToDictMixin.dump_obj(self)

    def to_json(self):
        return json.dumps(self.to_dict())

ToJsonMixin = ToDictMixin