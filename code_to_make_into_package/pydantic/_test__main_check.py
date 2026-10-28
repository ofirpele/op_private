from pathlib import Path
from textwrap import dedent

import pytest

from tai.pydantic.main_check import (
    _collect_violations,
    _print_violations,
    check_classvar,
    check_file,
    check_private_attr,
    check_private_field_defaults,
    main,
)


def test_encapsulation_violation_detected(tmp_path: Path):
    code = dedent("""
        class Foo:
            p_secret: int = 0

        def bad_access():
            obj = Foo()
            return obj.p_secret
    """)
    test_file = tmp_path / "test_encap.py"
    test_file.write_text(code)

    violations = check_file(test_file)

    assert len(violations) == 1
    assert violations[0][2] == "p_secret"


def test_encapsulation_self_access_allowed(tmp_path: Path):
    code = dedent("""
        class Foo:
            p_value: int = 0

            def get_value(self):
                return self.p_value
    """)
    test_file = tmp_path / "test_encap.py"
    test_file.write_text(code)

    violations = check_file(test_file)

    assert len(violations) == 0


def test_classvar_missing_detected(tmp_path: Path):
    code = dedent("""
        class Foo:
            _counter: int = 0
    """)
    test_file = tmp_path / "test_classvar.py"
    test_file.write_text(code)

    violations = check_classvar(test_file)

    assert len(violations) == 1
    assert violations[0][2] == "_counter"


def test_classvar_annotation_passes(tmp_path: Path):
    code = dedent("""
        from typing import ClassVar

        class Foo:
            _counter: ClassVar[int] = 0
    """)
    test_file = tmp_path / "test_classvar.py"
    test_file.write_text(code)

    violations = check_classvar(test_file)

    assert len(violations) == 0


def test_private_attr_import_detected(tmp_path: Path):
    code = dedent("""
        from pydantic import PrivateAttr

        class Foo:
            pass
    """)
    test_file = tmp_path / "test_private_attr.py"
    test_file.write_text(code)

    violations = check_private_attr(test_file)

    assert len(violations) == 1
    assert violations[0][2] == "import"


def test_private_attr_usage_detected(tmp_path: Path):
    code = dedent("""
        class Foo:
            _secret = PrivateAttr(default="hidden")
    """)
    test_file = tmp_path / "test_private_attr.py"
    test_file.write_text(code)

    violations = check_private_attr(test_file)

    assert len(violations) == 1
    assert violations[0][2] == "usage"


def test_p_field_without_default_detected(tmp_path: Path):
    code = dedent("""
        class Foo:
            p_value: int
    """)
    test_file = tmp_path / "test_p_default.py"
    test_file.write_text(code)

    violations = check_private_field_defaults(test_file)

    assert len(violations) == 1
    assert violations[0][2] == "p_value"


def test_p_field_with_default_passes(tmp_path: Path):
    code = dedent("""
        class Foo:
            p_value: int = 0
    """)
    test_file = tmp_path / "test_p_default.py"
    test_file.write_text(code)

    violations = check_private_field_defaults(test_file)

    assert len(violations) == 0


def test_p_field_with_field_default_factory_passes(tmp_path: Path):
    code = dedent("""
        from pydantic import Field

        class Foo:
            p_items: list = Field(default_factory=list)
    """)
    test_file = tmp_path / "test_p_default.py"
    test_file.write_text(code)

    violations = check_private_field_defaults(test_file)

    assert len(violations) == 0


def test_valid_code_passes_all_checks(tmp_path: Path):
    code = dedent("""
        from typing import ClassVar
        from pydantic import Field

        class ValidModel:
            _counter: ClassVar[int] = 0
            p_value: int = 0
            p_items: list = Field(default_factory=list)

            def get_value(self):
                return self.p_value
    """)
    test_file = tmp_path / "test_valid.py"
    test_file.write_text(code)

    assert len(check_file(test_file)) == 0
    assert len(check_classvar(test_file)) == 0
    assert len(check_private_attr(test_file)) == 0
    assert len(check_private_field_defaults(test_file)) == 0


def test_syntax_error_returns_empty(tmp_path: Path):
    code = "def broken(:\n    pass"
    test_file = tmp_path / "test_syntax.py"
    test_file.write_text(code)

    assert check_file(test_file) == []
    assert check_classvar(test_file) == []
    assert check_private_attr(test_file) == []
    assert check_private_field_defaults(test_file) == []


def test_p_attr_via_assign_detected(tmp_path: Path):
    code = dedent("""
        class Foo:
            p_value = 0

        def bad_access():
            obj = Foo()
            return obj.p_value
    """)
    test_file = tmp_path / "test_assign.py"
    test_file.write_text(code)

    violations = check_file(test_file)

    assert len(violations) == 1


def test_access_expr_via_call(tmp_path: Path):
    code = dedent("""
        class Foo:
            p_value: int = 0

        def bad_access():
            return get_foo().p_value
    """)
    test_file = tmp_path / "test_call.py"
    test_file.write_text(code)

    violations = check_file(test_file)

    assert len(violations) == 1
    assert violations[0][3] == "(...).p_value"


def test_access_expr_other(tmp_path: Path):
    code = dedent("""
        class Foo:
            p_value: int = 0

        items = [Foo()]
        x = items[0].p_value
    """)
    test_file = tmp_path / "test_subscript.py"
    test_file.write_text(code)

    violations = check_file(test_file)

    assert len(violations) == 1
    assert violations[0][3] == "(...).p_value"


def test_access_expr_unknown_node_type(tmp_path: Path):
    code = dedent("""
        class Foo:
            p_value: int = 0

        x = (Foo(),).p_value
    """)
    test_file = tmp_path / "test_tuple.py"
    test_file.write_text(code)

    violations = check_file(test_file)

    assert len(violations) == 1
    assert violations[0][3] == "?.p_value"


def test_classvar_typing_attribute_form(tmp_path: Path):
    code = dedent("""
        import typing

        class Foo:
            _counter: typing.ClassVar[int] = 0
    """)
    test_file = tmp_path / "test_typing_classvar.py"
    test_file.write_text(code)

    violations = check_classvar(test_file)

    assert len(violations) == 0


def test_private_attr_via_module_attribute(tmp_path: Path):
    code = dedent("""
        import pydantic

        class Foo:
            _secret = pydantic.PrivateAttr(default="hidden")
    """)
    test_file = tmp_path / "test_pydantic_attr.py"
    test_file.write_text(code)

    violations = check_private_attr(test_file)

    assert len(violations) == 1
    assert violations[0][2] == "usage"


def test_main_returns_zero_on_valid_codebase():
    exit_code = main()

    assert exit_code == 0


def test_collect_violations_skips_test_and_main_files(tmp_path: Path):
    (tmp_path / "_test__foo.py").write_text("x = obj.p_value")
    (tmp_path / "main_bar.py").write_text("x = obj.p_value")
    (tmp_path / "valid.py").write_text("class Foo:\n    p_value: int = 0")

    violations = _collect_violations(tmp_path)

    assert violations["encap"] == []


def test_print_violations_with_encap(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    violations = {
        "encap": [(tmp_path / "test.py", 10, "p_value", "obj.p_value")],
        "classvar": [],
        "private_attr": [],
        "p_field_default": [],
    }

    exit_code = _print_violations(violations, tmp_path)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Encapsulation violations found" in captured.out


def test_print_violations_with_classvar(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    violations = {
        "encap": [],
        "classvar": [(tmp_path / "test.py", 10, "_counter")],
        "private_attr": [],
        "p_field_default": [],
    }

    exit_code = _print_violations(violations, tmp_path)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "ClassVar annotation missing" in captured.out


def test_print_violations_with_private_attr(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    violations = {
        "encap": [],
        "classvar": [],
        "private_attr": [(tmp_path / "test.py", 10, "import")],
        "p_field_default": [],
    }

    exit_code = _print_violations(violations, tmp_path)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "PrivateAttr usage found" in captured.out


def test_print_violations_with_p_field_default(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    violations = {
        "encap": [],
        "classvar": [],
        "private_attr": [],
        "p_field_default": [(tmp_path / "test.py", 10, "p_value")],
    }

    exit_code = _print_violations(violations, tmp_path)

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "p_ fields without defaults" in captured.out


def test_print_violations_returns_zero_when_no_violations(tmp_path: Path):
    violations = {
        "encap": [],
        "classvar": [],
        "private_attr": [],
        "p_field_default": [],
    }

    exit_code = _print_violations(violations, tmp_path)

    assert exit_code == 0
