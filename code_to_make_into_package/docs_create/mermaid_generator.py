import re

from tai.docs_create.config import ClassInfo, DiagramConfig, MethodInfo


def generate_class_diagram(classes: list[ClassInfo], config: DiagramConfig) -> str:
    lines = ["classDiagram"]

    for class_info in classes:
        if class_info.name in config.classes_to_skip:
            continue

        class_lines = format_class_with_methods(class_info, config)
        lines.extend(class_lines)

    inheritance_lines = generate_inheritance_relationships(classes, config)
    lines.extend(inheritance_lines)

    return "\n".join(lines)


def format_class_with_methods(class_info: ClassInfo, config: DiagramConfig) -> list[str]:
    lines = []
    class_name = escape_mermaid_special_chars(class_info.name)
    lines.append(f"    class {class_name} {{")

    if config.include_attributes:
        for attr_name, attr_type in class_info.attributes:
            attr_line = f"        {attr_name}"
            if attr_type:
                attr_line += f": {escape_mermaid_special_chars(attr_type)}"
            lines.append(attr_line)

    method_count = 0
    for method in class_info.methods:
        if method_count >= config.max_method_count:
            lines.append("        ...")
            break

        if not should_include_method(method, config):
            continue

        method_line = format_method_signature(method)
        lines.append(method_line)
        method_count += 1

    lines.append("    }")

    return lines


def should_include_method(method: MethodInfo, config: DiagramConfig) -> bool:
    if method.name.startswith("_") and not config.include_private_methods:
        return False

    if method.is_property and not config.include_properties:
        return False

    if method.is_classmethod and not config.include_class_methods:
        return False

    if method.is_staticmethod and not config.include_static_methods:
        return False

    return not (method.is_abstract and not config.include_abstract_methods)


def format_method_signature(method: MethodInfo) -> str:
    method_name = escape_mermaid_special_chars(method.name)

    params = []
    for param in method.parameters:
        param_str = param.name
        if param.type_hint:
            param_str += f": {escape_mermaid_special_chars(param.type_hint)}"
        params.append(param_str)

    signature = f"        {method_name}({', '.join(params)})"

    if method.return_type and method.return_type != "None":
        signature += f" {escape_mermaid_special_chars(method.return_type)}"

    if method.is_abstract:
        signature += "*"

    return signature


def clean_type_hint(type_hint: str) -> str:
    if type_hint is None:
        return ""

    conlist_pattern = r"conlist\(([^,]+)(?:,\s*[^)]+)?\)"
    type_hint = re.sub(conlist_pattern, r"list[\1]", type_hint)

    return type_hint.replace("pnd.Np1DArrayFp64", "np_1d_fp64")


def escape_mermaid_special_chars(text: str) -> str:
    if text is None:
        return ""

    text = clean_type_hint(text)

    replacements = {
        "<": "&#60;",
        ">": "&#62;",
        "{": "&#123;",
        "}": "&#125;",
        "|": "&#124;",
    }

    result = text
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)

    return result


def generate_inheritance_relationships(
    classes: list[ClassInfo], config: DiagramConfig
) -> list[str]:
    lines = []

    for class_info in classes:
        if class_info.name in config.classes_to_skip:
            continue

        class_name = escape_mermaid_special_chars(class_info.name)

        for base_class in class_info.base_classes:
            if base_class in config.classes_to_skip:
                continue

            base_name = escape_mermaid_special_chars(base_class)
            lines.append(f"    {base_name} <|-- {class_name}")

    return lines
