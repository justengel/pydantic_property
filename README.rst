================
pydantic_property
================

Added a field_property which gives property like functionality to pydantic models.

Note:

    Due to the way pydantic is written the field_property will be slow and inefficient.
    Pydantic heavily uses and modifies the __dict__ attribute while overloading __setattr__.
    Additionally, Pydantic's metaclass modifies the class __dict__ before class creation removing all
    property objects from the class definition.
    These changes prevent property objects and normal descriptors from working.

    To work around this setting the field_property value must run the normal pydantic __setattr__,
    run the object __setattr__ to call the property setter, and must update the __dict__ with all field_property values.
    The Pydantic model __dict__ is only updated on __setattr__ and does not dynamically retrieve values.


Simple Example
==============

.. code-block:: python

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


Pydantic Notes Example
======================

Pydantic __dict__ Example below does not work, but shows what pydantic is doing in the background.

.. code-block:: python

    from pydantic import BaseModel, PrivateAttr

    class MyModel(BaseModel):
        x: int = 1

        # Property doesn't really work. This is to show what pydantic does.
        _y: int = PrivateAttr(default=1)

        @property
        def y(self):
            return self._y

        @y.setter
        def y(self, value):
            self._y = value

        def set_point(self, x, y):
            self.x = x
            self._y = y

    m = MyModel()
    m.x = 2  # This actually sets self.__dict__['x'] = 2
    assert m.dict() == {'x': 2}

    m.y = 3  # Essentially this would change self.__dict__['y'] = 2
    assert m.dict() == {'x': 2, 'y': 3}
    assert m.__dict__ == {'x': 2, 'y': 3}

    # This sets self.__dict__['x'] = 4 and the instance value m._y to 5, but does not change self.__dict__['y']
    m.set_point(4, 5)
    m.dict() == {'x': 4, 'y': 3}  # y is not updated ._y is 5. self.__dict__['y'] still == 3

    # This is why field_property must update __dict__ for all field_property values.
    # This makes the field_property inefficient.
