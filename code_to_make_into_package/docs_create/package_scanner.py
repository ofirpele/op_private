import ast
from pathlib import Path


def scan_package(package_path: str) -> list[str]:
    module_paths = []
    path = Path(package_path)

    if not path.exists():
        return module_paths

    if path.is_file() and path.suffix == ".py":
        module_paths.append(str(path))
        return module_paths

    for root_path in path.rglob("*.py"):
        if not root_path.name.startswith("_test_") and root_path.is_file():
            parent_parts = root_path.relative_to(path).parent.parts
            if not any(p.startswith("_") and p != "__pycache__" for p in parent_parts):
                module_paths.append(str(root_path))

    return module_paths


def get_module_source(module_path: str) -> str | None:
    try:
        return Path(module_path).read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return None


def parse_module(source_code: str) -> ast.Module | None:
    try:
        return ast.parse(source_code)
    except SyntaxError:
        return None


def extract_classes_from_module(module: ast.Module) -> list[ast.ClassDef]:
    return [node for node in ast.walk(module) if isinstance(node, ast.ClassDef)]


def get_classes_from_path(module_path: str) -> list[tuple[ast.ClassDef, str]]:
    source = get_module_source(module_path)
    if not source:
        return []

    module = parse_module(source)
    if not module:
        return []

    classes = extract_classes_from_module(module)
    return [(cls, module_path) for cls in classes]
