
def test_private_attributes():
    from pydantic import BaseModel, PrivateAttr

    class Test(BaseModel):
        _x: int = PrivateAttr(default=0)

    t = Test()
    print(t.dict())
    t._x = 1
    print(t.dict())


def test_field_property():
    from pydantic import PrivateAttr
    from pydantic_property import PropertyModel, field_property

    class Props(PropertyModel):
        x: int = field_property('_x', default=0)  # getter is created with '_x'

        @x.setter
        def x(self, value):
            self._x = value  # Note: matches field_property('_x')

        y: int = field_property('_y', default=0)  # Need to define '_y' for __private_attribute__

        @y.getter
        def y(self) -> int:
            return getattr(self, '_y', 0)

        @y.setter
        def y(self, value):
            if isinstance(value, float):
                self._x = int((value % 1) * 10)  # Must update all field_property with __dict__ for _x to be seen
            self._y = int(value)

        # Does not have a __private_attribute__ so '_z' will fail. we hack this later for testing
        @field_property(default=0)
        def z(self):
            return getattr(self, '_z', 0)

        @z.setter
        def z(self, value):
            self._z = value

        # Have to add private attribute to allow _z to work.
        # z.private_name = '_z'
        # or
        _z = PrivateAttr(default=0)  # field_property.PrivateAttr

    p = Props()
    print(p)
    p.x = 2
    p.y = 1.5
    print(p)

    assert p.x == 5, '{} != {}'.format(p.x, 5)
    assert p.y == 1, '{} != {}'.format(p.y, 1)

    msg = p.dict()
    assert p.x == msg['x'], '{} != {}'.format(p.x, msg['x'])
    assert p.y == msg['y'], '{} != {}'.format(p.y, msg['y'])
    assert p.z == msg['z'], '{} != {}'.format(p.z, msg['z'])


if __name__ == '__main__':
    # test_private_attributes()
    test_field_property()

    print('All tests finished successfully!')
