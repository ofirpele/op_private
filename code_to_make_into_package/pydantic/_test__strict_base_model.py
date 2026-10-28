import copy
import logging
from typing import Any, Self

import pytest
from pydantic import Field, PrivateAttr, ValidationError
from sortedcontainers_pydantic import AnnotatedSortedSet

from tai.pydantic.strict_base_model import StrictBaseModel

_TOY_FORBIDDEN_A = -3


class _Toy(StrictBaseModel):
    a: int
    b: str

    def __post_init__(self):
        assert self.a != _TOY_FORBIDDEN_A


def test_strict_base_model(caplog):  # noqa: ANN001
    t = _Toy(a=3, b="ff")
    assert str(t) == '_Toy\n{\n  "a": 3,\n  "b": "ff"\n}'
    assert repr(t) == str(t)

    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit):
        _t = _Toy(a=_TOY_FORBIDDEN_A, b="")
    assert (
        '(<class \'AssertionError\'>, AssertionError(\'assert -3 != -3\\n +  where -3 = _Toy\\\\n{\\\\n  "a": -3,\\\\n  "b": ""\\\\n}.a\'), <traceback object at'  # noqa: E501
        in str(caplog.records[0].exc_info)
    )

    with pytest.raises(TypeError):

        class _Toy2(_Toy):
            def __init__(self):
                self.a = 3

    with pytest.raises(
        TypeError, match="defines model_post_init but inherits from StrictBaseModel"
    ):

        class _Toy3(_Toy):
            def model_post_init(self, _: object) -> None:
                pass  # not allowed in StrictBaseModel


class _SortedFloatPairs(StrictBaseModel):
    entries: StrictBaseModel.DeleteAfterPostInit(list[tuple[float, float]])
    p_sorted_set: AnnotatedSortedSet = Field(default_factory=AnnotatedSortedSet)

    def __post_init__(self):
        self.p_sorted_set = AnnotatedSortedSet(self.entries, key=lambda x: x[0])


def test_delete_after_init_entries_deleted():
    pairs = _SortedFloatPairs(entries=[(3.0, 1.0), (1.0, 5.0)])

    assert not hasattr(pairs, "entries")
    assert list(pairs.p_sorted_set) == [(1.0, 5.0), (3.0, 1.0)]


def test_delete_after_init_empty_entries():
    pairs = _SortedFloatPairs(entries=[])

    assert list(pairs.p_sorted_set) == []


class _MultiFieldDelete(StrictBaseModel):
    temp_x: StrictBaseModel.DeleteAfterPostInit(list[float])
    name: str
    temp_y: StrictBaseModel.DeleteAfterPostInit(list[float])
    scale: float
    p_sum_x: float = 0.0
    p_sum_y: float = 0.0

    def __post_init__(self):
        self.p_sum_x = sum(self.temp_x) * self.scale
        self.p_sum_y = sum(self.temp_y) * self.scale


def test_delete_after_init_multiple_fields_deleted():
    obj = _MultiFieldDelete(temp_x=[1.0, 2.0], temp_y=[3.0, 4.0], name="test", scale=2.0)

    assert not hasattr(obj, "temp_x")
    assert not hasattr(obj, "temp_y")


def test_delete_after_init_regular_fields_preserved():
    obj = _MultiFieldDelete(temp_x=[1.0, 2.0], temp_y=[3.0, 4.0], name="test", scale=2.0)

    assert obj.name == "test"
    assert obj.scale == 2.0


def test_delete_after_init_computed_values_correct():
    obj = _MultiFieldDelete(temp_x=[1.0, 2.0], temp_y=[3.0, 4.0], name="test", scale=2.0)

    assert obj.p_sum_x == 6.0  # (1+2) * 2
    assert obj.p_sum_y == 14.0  # (3+4) * 2


def test_private_field_cannot_be_passed_during_init():
    with pytest.raises(
        ValueError, match="Field 'p_sum_x' is private and cannot be passed during init"
    ):
        _MultiFieldDelete(temp_x=[1.0], temp_y=[2.0], name="test", scale=1.0, p_sum_x=99.0)


def test_no_private_allowed():
    with pytest.raises(
        TypeError, match=r"uses PrivateAttr or field that starts with _ \(\['_secret'\]\)"
    ):

        class _BadModel1(StrictBaseModel):
            name: str
            _secret: str = PrivateAttr(default="hidden")

    with pytest.raises(
        TypeError, match=r"uses PrivateAttr or field that starts with _ \(\['_secret'\]\)"
    ):

        class _BadModel2(StrictBaseModel):
            name: str
            _secret: str

    with pytest.raises(NameError, match="Private attributes must not use valid field names"):

        class _BadModel3(StrictBaseModel):
            name: str
            secret: str = PrivateAttr(default="hidden")


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        _Toy(a=1, b="test", extra_field="not_allowed")


def test_strict_mode_rejects_type_coercion():
    with pytest.raises(ValidationError):
        _Toy(a="not_an_int", b="test")


# ============================================================================
# Deep Copy Tests
# ============================================================================


class _DeepCopyParent(StrictBaseModel):
    name: str
    values: list[int]
    p_computed: int = 0

    def __post_init__(self):
        self.p_computed = sum(self.values)


class _DeepCopyChild(_DeepCopyParent):
    child_field: float

    def _deep_copy_impl(self, new_obj: Self, _memo: dict[int, Any]) -> None:
        new_obj.p_computed = new_obj.p_computed * 2


class _DeepCopyGrandchild(_DeepCopyChild):
    grandchild_field: str

    def _deep_copy_impl(self, new_obj: Self, _memo: dict[int, Any]) -> None:
        super()._deep_copy_impl(new_obj, _memo)
        new_obj.p_computed = new_obj.p_computed + 100


def test_deepcopy_basic():
    original = _DeepCopyParent(name="test", values=[1, 2, 3])
    copied = copy.deepcopy(original)

    assert copied.name == original.name
    assert copied.values == original.values
    assert copied.p_computed == original.p_computed
    assert copied is not original
    assert copied.values is not original.values


def test_deepcopy_modifying_copy_does_not_affect_original():
    original = _DeepCopyParent(name="test", values=[1, 2, 3])
    copied = copy.deepcopy(original)

    copied.values.append(4)
    copied.name = "modified"

    assert original.values == [1, 2, 3]
    assert original.name == "test"


def test_deepcopy_child_with_deep_copy_impl():
    original = _DeepCopyChild(name="child", values=[1, 2, 3], child_field=1.5)
    assert original.p_computed == 6

    copied = copy.deepcopy(original)

    assert copied.name == original.name
    assert copied.values == original.values
    assert copied.child_field == original.child_field
    assert copied.p_computed == 12  # 6 * 2 from _deep_copy_impl


def test_deepcopy_grandchild_with_chained_deep_copy_impl():
    original = _DeepCopyGrandchild(
        name="grandchild", values=[1, 2, 3], child_field=1.5, grandchild_field="gc"
    )
    assert original.p_computed == 6

    copied = copy.deepcopy(original)

    assert copied.name == original.name
    assert copied.grandchild_field == original.grandchild_field
    assert copied.p_computed == 112  # (6 * 2) + 100 from chained _deep_copy_impl


def test_deepcopy_equality():
    original = _DeepCopyParent(name="test", values=[1, 2, 3])
    copied = copy.deepcopy(original)

    assert original == copied


def test_deepcopy_with_memo_prevents_duplicate_copies():
    class _Container(StrictBaseModel):
        item: _DeepCopyParent

    shared_item = _DeepCopyParent(name="shared", values=[1])
    container = _Container(item=shared_item)

    memo: dict[int, Any] = {}
    copied_container = copy.deepcopy(container, memo)

    assert copied_container.item is not container.item
    assert id(container.item) in memo
    assert memo[id(container.item)] is copied_container.item


def test_deepcopy_circular_reference():
    class _Node(StrictBaseModel):
        value: int
        p_next: "_Node | None" = None

    node1 = _Node(value=1)
    node2 = _Node(value=2)
    node1.p_next = node2
    node2.p_next = node1

    copied_node1 = copy.deepcopy(node1)

    assert copied_node1 is not node1
    assert copied_node1.p_next is not node2

    copied_node2 = copied_node1.p_next
    assert copied_node1.p_next is copied_node2
    assert copied_node2.p_next is copied_node1  # circular ref preserved
    assert copied_node1.value == 1
    assert copied_node2.value == 2


def test_deepcopy_same_object_referenced_twice():
    class _Wrapper(StrictBaseModel):
        first: _DeepCopyParent
        second: _DeepCopyParent

    shared = _DeepCopyParent(name="shared", values=[1, 2])
    wrapper = _Wrapper(first=shared, second=shared)

    assert wrapper.first is wrapper.second

    copied = copy.deepcopy(wrapper)

    assert copied.first is not shared
    assert copied.first is copied.second  # same object referenced twice


def test_deepcopy_self_reference():
    class _SelfRef(StrictBaseModel):
        value: int
        p_self: "_SelfRef | None" = None

    obj = _SelfRef(value=42)
    obj.p_self = obj  # self reference

    copied = copy.deepcopy(obj)

    assert copied is not obj
    assert copied.p_self is copied  # self reference preserved
    assert copied.value == 42


def test_deepcopy_returns_cached_from_memo():
    original = _DeepCopyParent(name="test", values=[1, 2, 3])
    memo: dict[int, Any] = {}

    copied_first = original.__deepcopy__(memo)
    copied_second = original.__deepcopy__(memo)

    assert copied_first is copied_second  # same object returned from memo
