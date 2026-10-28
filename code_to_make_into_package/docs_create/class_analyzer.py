import ast

from tai.docs_create.config import ClassInfo, MethodInfo, ParameterInfo


def analyze_class(class_node: ast.ClassDef, module_path: str) -> ClassInfo:
    base_classes = extract_base_classes(class_node)
    methods = extract_methods(class_node)
    attributes = extract_attributes(class_node)

    return ClassInfo(
        name=class_node.name,
        module_path=module_path,
        base_classes=base_classes,
        methods=methods,
        attributes=attributes,
    )


def extract_base_classes(class_node: ast.ClassDef) -> list[str]:
    base_classes = []
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            base_classes.append(base.id)
        elif isinstance(base, ast.Attribute):
            parts = []
            node = base
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            base_classes.append(".".join(reversed(parts)))
    return base_classes


def extract_methods(class_node: ast.ClassDef) -> list[MethodInfo]:
    methods = []
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef):
            if not is_public_method(node.name):
                continue

            method_info = extract_method_signature(node)
            methods.append(method_info)

    return methods


def is_public_method(method_name: str) -> bool:
    return not method_name.startswith("_")


def extract_method_signature(method_node: ast.FunctionDef) -> MethodInfo:
    parameters = extract_parameters(method_node)
    return_type = get_return_type(method_node)
    decorators = detect_decorators(method_node)

    return MethodInfo(
        name=method_node.name,
        parameters=parameters,
        return_type=return_type,
        is_property=decorators.get("property", False),
        is_classmethod=decorators.get("classmethod", False),
        is_staticmethod=decorators.get("staticmethod", False),
        is_abstract=decorators.get("abstractmethod", False),
    )


def extract_parameters(method_node: ast.FunctionDef) -> list[ParameterInfo]:
    parameters = []
    args = method_node.args

    defaults_offset = len(args.args) - len(args.defaults)

    for i, arg in enumerate(args.args):
        if arg.arg in {"self", "cls"}:
            continue

        param_info = get_parameter_info(arg)

        default_idx = i - defaults_offset
        if default_idx >= 0 and default_idx < len(args.defaults):
            default = args.defaults[default_idx]
            param_info.default_value = (
                ast.unparse(default) if hasattr(ast, "unparse") else str(default)
            )

        parameters.append(param_info)

    if args.vararg:
        param = ParameterInfo(
            name=f"*{args.vararg.arg}",
            type_hint=get_type_hint(args.vararg.annotation),
            default_value=None,
        )
        parameters.append(param)

    kw_defaults_dict = {
        arg.arg: default for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True)
    }

    for arg in args.kwonlyargs:
        param_info = get_parameter_info(arg)

        default = kw_defaults_dict.get(arg.arg)
        if default is not None:
            param_info.default_value = (
                ast.unparse(default) if hasattr(ast, "unparse") else str(default)
            )

        parameters.append(param_info)

    if args.kwarg:
        param = ParameterInfo(
            name=f"**{args.kwarg.arg}",
            type_hint=get_type_hint(args.kwarg.annotation),
            default_value=None,
        )
        parameters.append(param)

    return parameters


def get_parameter_info(arg: ast.arg) -> ParameterInfo:
    return ParameterInfo(name=arg.arg, type_hint=get_type_hint(arg.annotation), default_value=None)


def get_type_hint(annotation: ast.expr | None) -> str | None:
    if annotation is None:
        return None

    if hasattr(ast, "unparse"):
        return ast.unparse(annotation)

    result = None
    if isinstance(annotation, ast.Name):
        result = annotation.id
    elif isinstance(annotation, ast.Attribute):
        parts = []
        node = annotation
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        result = ".".join(reversed(parts))
    elif isinstance(annotation, ast.Subscript):
        value = get_type_hint(annotation.value)
        slice_val = get_type_hint(annotation.slice)
        result = f"{value}[{slice_val}]"
    elif isinstance(annotation, ast.Constant):
        result = repr(annotation.value)
    else:
        result = str(annotation)

    return result


def get_return_type(method_node: ast.FunctionDef) -> str | None:
    return get_type_hint(method_node.returns)


def detect_decorators(method_node: ast.FunctionDef) -> dict[str, bool]:
    decorators = {
        "property": False,
        "classmethod": False,
        "staticmethod": False,
        "abstractmethod": False,
    }

    for decorator in method_node.decorator_list:
        if isinstance(decorator, ast.Name):
            if decorator.id in decorators:
                decorators[decorator.id] = True
        elif isinstance(decorator, ast.Attribute) and decorator.attr in decorators:
            decorators[decorator.attr] = True

    return decorators


def extract_attributes(class_node: ast.ClassDef) -> list[tuple[str, str | None]]:
    attributes = []

    for node in class_node.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if not name.startswith("_"):
                type_hint = get_type_hint(node.annotation)
                attributes.append((name, type_hint))
        elif isinstance(node, ast.Assign):
            attributes.extend(
                (target.id, None)
                for target in node.targets
                if isinstance(target, ast.Name) and not target.id.startswith("_")
            )

    return attributes
