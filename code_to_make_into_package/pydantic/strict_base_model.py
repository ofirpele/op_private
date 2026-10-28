import copy
import logging
import sys
import traceback
from typing import Annotated, Any, Self, get_args, get_origin

from pydantic import BaseModel, ConfigDict


class _DeleteAfterPostInitMarker:
    pass


class StrictBaseModel(BaseModel):
    """
    Differences from BaseModel:
     - PrivateAttr is not allowed (main_check.py + runtime)
     - Fields starting with "_" that are not ClassVar are not allowed (main_check.py + runtime)
     - Fields starting with "p_" are treated as "private":
       - Cannot be passed during init (runtime)
       - Must have defaults (main_check.py)
     - Use DeleteAfterPostInit for params that are sent to init but deleted after __post_init__.
       This is useful for example, for getting as input a list and creating a private field (p_)
       that is an AnnotatedSortedSet (pydantic wrapper around sorted set)
     - Defaults: extra="forbid", strict=True
     - No __init__ or model_post_init allowed (runtime)
       Use __post_init__ instead
     - str and repr include class name and json
     - Custom __deepcopy__ that handles pydantic internals. Override _deep_copy_impl for
       class-specific deep copy logic.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    def _deep_copy_impl(self, new_obj: Self, memo: dict[int, Any]) -> None:
        pass  # Override in subclasses for class-specific deep copy logic

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        # memo is a dict that maps id(original_obj) -> copied_obj.
        # It prevents infinite recursion for circular references and ensures
        # that if the same object appears multiple times, it's only copied once.
        if id(self) in memo:
            return memo[id(self)]

        new_obj = object.__new__(type(self))
        # Register early so nested deepcopy calls find it
        memo[id(self)] = new_obj

        # Initialize pydantic internals (required for pydantic model to function)
        object.__setattr__(new_obj, "__pydantic_fields_set__", set())
        object.__setattr__(new_obj, "__pydantic_private__", None)
        object.__setattr__(new_obj, "__pydantic_extra__", None)

        # Deep copy all model fields
        for field_name in type(self).model_fields:
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                object.__setattr__(new_obj, field_name, copy.deepcopy(value, memo))

        # Call class-specific deep copy logic if it exists
        if hasattr(self, "_deep_copy_impl"):
            self._deep_copy_impl(new_obj, memo)

        return new_obj

    def __init_subclass__(cls, **kwargs: object) -> None:
        def raise_type_error(msg: str) -> None:
            traceback.print_exc()
            raise TypeError(msg)

        super().__init_subclass__(**kwargs)

        if cls.__private_attributes__:
            attr_names = list(cls.__private_attributes__.keys())
            raise_type_error(
                f"{cls.__name__} uses PrivateAttr or field that starts with _ ({attr_names})"
                f"which is not allowed in StrictBaseModel. Use p_ prefixed fields instead."
            )

        for method in ("__init__", "model_post_init"):
            if method in cls.__dict__:
                raise_type_error(
                    f"{cls.__name__} defines {method} but inherits from StrictBaseModel. "
                    f"Use __post_init__ instead."
                )

    @staticmethod
    def DeleteAfterPostInit(type_: type) -> type:  # noqa: N802
        return Annotated[type_, _DeleteAfterPostInitMarker()]

    @classmethod
    def _get_delete_after_post_init_fields(cls) -> list[str]:
        fields_to_delete = []
        for field_name, annotation in cls.__annotations__.items():
            if get_origin(annotation) is Annotated:
                for arg in get_args(annotation):
                    if isinstance(arg, _DeleteAfterPostInitMarker):
                        fields_to_delete.append(field_name)
                        break
        return fields_to_delete

    def model_post_init(self, _: object, /) -> None:
        for field_name in self.__pydantic_fields_set__:
            if field_name.startswith("p_"):
                msg = f"Field '{field_name}' is private and cannot be passed during init"
                raise ValueError(msg)

        for cls in type(self).__mro__:
            if "__post_init__" in cls.__dict__:
                try:
                    cls.__post_init__(self)
                except AssertionError:
                    logging.exception("")
                    sys.exit()

        for field_name in self._get_delete_after_post_init_fields():
            delattr(self, field_name)

    def __str__(self):
        return self.__class__.__name__ + "\n" + self.model_dump_json(indent=2, by_alias=True)

    def __repr__(self):
        return self.__str__()
