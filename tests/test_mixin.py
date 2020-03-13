
from basepy.mixins import ToDictMixin

class Foo:
    def __init__(self):
        self.bar = 'bar'
        self.value = 123

    def echo(self):
        print(self.bar)

def test_to_dict_mixin():
    f = Foo()
    r = ToDictMixin.dump_obj(f)
    print(r)
    assert len(r) == 2
    assert r['bar'] == 'bar'
    assert r['value'] == 123