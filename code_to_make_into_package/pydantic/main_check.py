import ast
import sys
from pathlib import Path


class EncapsulationChecker(ast.NodeVisitor):
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.violations: list[tuple[int, str, str]] = []
        self.current_class: str | None = None
        self.current_class_p_attrs: set[str] = set()

    def _collect_class_p_attrs(self, node: ast.ClassDef) -> set[str]:
        p_attrs = set()
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                if item.target.id.startswith("p_"):
                    p_attrs.add(item.target.id)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id.startswith("p_"):
                        p_attrs.add(target.id)
        return p_attrs

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        old_class = self.current_class
        old_p_attrs = self.current_class_p_attrs
        self.current_class = node.name
        self.current_class_p_attrs = self._collect_class_p_attrs(node)
        self.generic_visit(node)
        self.current_class = old_class
        self.current_class_p_attrs = old_p_attrs

    def _get_access_expr(self, node: ast.Attribute) -> str:
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        if isinstance(node.value, (ast.Attribute, ast.Call, ast.Subscript)):
            return f"(...).{node.attr}"
        return f"?.{node.attr}"

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("p_"):
            is_self_access = isinstance(node.value, ast.Name) and node.value.id == "self"
            is_same_class_attr = (
                self.current_class is not None and node.attr in self.current_class_p_attrs
            )
            if not (is_self_access or is_same_class_attr):
                self.violations.append((node.lineno, node.attr, self._get_access_expr(node)))
        self.generic_visit(node)


def check_file(filepath: Path) -> list[tuple[Path, int, str, str]]:
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    checker = EncapsulationChecker(filepath)
    checker.visit(tree)
    return [(filepath, line, attr, expr) for line, attr, expr in checker.violations]


def _is_classvar_annotation(annotation: ast.expr) -> bool:
    if isinstance(annotation, ast.Subscript):
        if isinstance(annotation.value, ast.Name) and annotation.value.id == "ClassVar":
            return True
        if isinstance(annotation.value, ast.Attribute) and annotation.value.attr == "ClassVar":
            return True
    return False


class ClassVarChecker(ast.NodeVisitor):
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.violations: list[tuple[int, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                name = item.target.id
                is_single_underscore_prefix = name.startswith("_") and not name.startswith("__")
                if is_single_underscore_prefix and not _is_classvar_annotation(item.annotation):
                    self.violations.append((item.lineno, name))
        self.generic_visit(node)


def check_classvar(filepath: Path) -> list[tuple[Path, int, str]]:
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    checker = ClassVarChecker(filepath)
    checker.visit(tree)
    return [(filepath, line, attr) for line, attr in checker.violations]


class PrivateAttrChecker(ast.NodeVisitor):
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.violations: list[tuple[int, str]] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "pydantic":
            for alias in node.names:
                if alias.name == "PrivateAttr":
                    self.violations.append((node.lineno, "import"))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        is_name_private_attr = isinstance(node.func, ast.Name) and node.func.id == "PrivateAttr"
        is_attr_private_attr = (
            isinstance(node.func, ast.Attribute) and node.func.attr == "PrivateAttr"
        )
        if is_name_private_attr or is_attr_private_attr:
            self.violations.append((node.lineno, "usage"))
        self.generic_visit(node)


def check_private_attr(filepath: Path) -> list[tuple[Path, int, str]]:
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    checker = PrivateAttrChecker(filepath)
    checker.visit(tree)
    return [(filepath, line, kind) for line, kind in checker.violations]


class PrivateFieldDefaultChecker(ast.NodeVisitor):
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.violations: list[tuple[int, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                name = item.target.id
                if name.startswith("p_") and item.value is None:
                    self.violations.append((item.lineno, name))
        self.generic_visit(node)


def check_private_field_defaults(filepath: Path) -> list[tuple[Path, int, str]]:
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    checker = PrivateFieldDefaultChecker(filepath)
    checker.visit(tree)
    return [(filepath, line, attr) for line, attr in checker.violations]


def _collect_violations(src_dir: Path) -> dict:
    violations = {
        "encap": [],
        "classvar": [],
        "private_attr": [],
        "p_field_default": [],
    }
    for py_file in src_dir.rglob("*.py"):
        if py_file.name.startswith("_test__") or py_file.name.startswith("main_"):
            continue
        violations["encap"].extend(check_file(py_file))
        violations["classvar"].extend(check_classvar(py_file))
        violations["private_attr"].extend(check_private_attr(py_file))
        violations["p_field_default"].extend(check_private_field_defaults(py_file))
    return violations


def _print_violations(violations: dict, src_dir: Path) -> int:
    exit_code = 0
    if violations["encap"]:
        print("Encapsulation violations found:")  # noqa: T201
        for filepath, line, attr, expr in sorted(violations["encap"]):
            rel_path = filepath.relative_to(src_dir.parent.parent)
            print(f"  {rel_path}:{line}: external access to '{attr}' via '{expr}'")  # noqa: T201
        exit_code = 1

    if violations["classvar"]:
        print("ClassVar annotation missing for underscore-prefixed class attributes:")  # noqa: T201
        for filepath, line, attr in sorted(violations["classvar"]):
            rel_path = filepath.relative_to(src_dir.parent.parent)
            print(f"  {rel_path}:{line}: '{attr}' should use ClassVar annotation")  # noqa: T201
        exit_code = 1

    if violations["private_attr"]:
        print("PrivateAttr usage found (not allowed in StrictBaseModel):")  # noqa: T201
        for filepath, line, kind in sorted(violations["private_attr"]):
            rel_path = filepath.relative_to(src_dir.parent.parent)
            print(f"  {rel_path}:{line}: PrivateAttr {kind}")  # noqa: T201
        exit_code = 1

    if violations["p_field_default"]:
        print("p_ fields without defaults found:")  # noqa: T201
        for filepath, line, attr in sorted(violations["p_field_default"]):
            rel_path = filepath.relative_to(src_dir.parent.parent)
            print(f"  {rel_path}:{line}: '{attr}' must have a default value")  # noqa: T201
        exit_code = 1

    return exit_code


def main() -> int:
    src_dir = Path(__file__).parent.parent
    violations = _collect_violations(src_dir)
    exit_code = _print_violations(violations, src_dir)

    if exit_code == 0:
        print("No violations found.")  # noqa: T201

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
