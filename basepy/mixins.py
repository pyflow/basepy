import json

class ToJsonMixin:
    def to_json(self):
        attrs = vars(self)
        for key, value in attrs.items():
            if hasattr(value, 'to_json'):
                attrs[key] = value.to_json()
        return json.dumps(attrs)
