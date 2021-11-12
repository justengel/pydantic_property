import sys
import inspect
from typing import Union, Callable, AbstractSet, Mapping, Any, Dict, ClassVar, Optional, Type, no_type_check
from pydantic.main import BaseModel
from pydantic.fields import FieldInfo, Undefined, Validator, UndefinedType, PrivateAttr
from pydantic.typing import NoArgAnyCallable


__all__ = ['field_property', 'PropertyModelMetaclass', 'PropertyModel']


has_set_name = sys.version_info >= (3, 6, 0)


class field_property(FieldInfo):

    PrivateAttr = PrivateAttr

    __slots__ = FieldInfo.__slots__ + (
        'public_name',
        'private_name',
        'fget',
        'fset',
        'fdel',
        )

    def __init__(self, fget=None, fset=None, fdel=None,
                 default: Any = Undefined,
                 public_name: str = None,
                 private_name: str = None,
                 *,
                 default_factory: Optional[NoArgAnyCallable] = None,
                 alias: str = None,
                 title: str = None,
                 description: str = None,
                 const: bool = None,
                 gt: float = None,
                 ge: float = None,
                 lt: float = None,
                 le: float = None,
                 multiple_of: float = None,
                 min_items: int = None,
                 max_items: int = None,
                 min_length: int = None,
                 max_length: int = None,
                 regex: str = None,
                 **extra: Any) -> None:

        if isinstance(fget, str):
            private_name = fget
            fget = self.internal_getter

            if public_name is None and private_name.startswith('_') and not private_name.startswith('__'):
                public_name = private_name[1:]
        elif fget is None:
            fget = self.internal_getter

        self.public_name = public_name
        self.private_name = private_name
        self.fget = fget
        self.fset = fset
        self.fdel = fdel

        if default is not Undefined and default_factory is not None:
            default_factory = inspect.signature(self.fget).return_annotation
            if default_factory == inspect.Signature.empty:
                default = None

        super().__init__(default,
                         default_factory=default_factory,
                         alias=alias,
                         title=title,
                         description=description,
                         const=const,
                         gt=gt,
                         ge=ge,
                         lt=lt,
                         le=le,
                         multiple_of=multiple_of,
                         min_items=min_items,
                         max_items=max_items,
                         min_length=min_length,
                         max_length=max_length,
                         regex=regex,
                         **extra,)

    def __set_name__(self, owner, name):
        self.public_name = name
        # self.private_name = '_' + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        self.fdel(obj)

    def get_default(self):
        """Return the default value for the instance."""
        if self.default != Undefined:
            return self.default
        elif self.default_factory is not None:
            return self.default_factory()
        return Undefined

    def get_type(self):
        default = self.get_default()
        if default == Undefined:
            return default
        return default.__class__

    def internal_getter(self, instance):
        try:
            return getattr(instance, self.private_name)
        except AttributeError as err:
            default = self.get_default()
            if default == Undefined:
                raise err from err

    def getter(self, fget):
        self.fget = fget
        return self

    __call__ = getter

    def setter(self, fset):
        self.fset = fset
        return self

    def deleter(self, fdel):
        self.fdel = fdel
        return self


class PropertyModelMetaclass(type(BaseModel)):
    """Metaclass to work with pydantic field_properties."""
    def __new__(mcs, name, bases, namespace, **kwargs):
        # Make the field_property visible as a field
        annotations = namespace.get('__annotations__', {})
        for varname, field in list(namespace.items()):
            if isinstance(field, field_property):
                # Validate the field info and check the annotation
                field._validate()
                if varname not in annotations:
                    annotations[varname] = field.get_type()

                # Add the private value
                if field.private_name:
                    namespace[field.private_name] = PrivateAttr(default=field.default,
                                                                default_factory=field.default_factory)

        new_cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # BaseModel metaclass (pydantic.ModelMetaclass) uses a custom namespace
        # the new class doesn't have the property attributes. This adds them back to the class
        field_properties = []
        for base in bases:
            field_properties.extend(getattr(base, '__field_properties__', []))
        for varname, field in namespace.items():
            if isinstance(field, field_property):
                # Add the descriptor
                setattr(new_cls, varname, field)
                field_properties.append(varname)

        new_cls.__field_properties__ = field_properties

        return new_cls


object_setattr = object.__setattr__
object_getattr = object.__getattribute__


class PropertyModel(BaseModel, metaclass=PropertyModelMetaclass):
    """Pydantic model that allows field_properties."""
    @no_type_check
    def __setattr__(self, name, value):  # noqa: C901 (ignore complexity)
        super().__setattr__(name, value)

        # This is depressing. Pydantic changes and heavily uses __dict__. So we have to call the property setter.
        # If the property setter modifies a private attribute __dict__ will not match
        # so we have to update __dict__ for all field_property objects.
        prop = getattr(self.__class__, name, None)
        if name in self.__dict__ and isinstance(prop, field_property):
            # Set the value
            object_setattr(self, name, value)  # normal setattr for property

            # Update all field properties. If private attributes were edited this will update the model properly
            self.__dict__.update({name: object_getattr(self, name)
                                  for name in getattr(self, '__field_properties__', [])})
