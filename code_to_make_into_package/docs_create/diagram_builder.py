from tai.docs_create.class_analyzer import analyze_class
from tai.docs_create.config import ClassInfo, DiagramConfig
from tai.docs_create.mermaid_generator import generate_class_diagram
from tai.docs_create.package_scanner import get_classes_from_path, scan_package


def build_diagram(package_path: str, config: DiagramConfig | None = None) -> str:
    if config is None:
        config = DiagramConfig(package_paths=[package_path])

    classes = collect_classes(package_path, config)
    all_classes_map = {cls.name: cls for cls in classes}
    classes = apply_filters(classes, config)
    classes = include_base_classes(classes, all_classes_map)

    if not classes:
        return 'classDiagram\n    note "No classes found"'

    classes = filter_inherited_methods(classes)

    return generate_class_diagram(classes, config)


def collect_classes(package_path: str, config: DiagramConfig) -> list[ClassInfo]:
    all_classes = []

    module_paths = scan_package(package_path)

    for module_path in module_paths:
        class_nodes = get_classes_from_path(module_path)

        for class_node, path in class_nodes:
            if class_node.name in config.classes_to_skip:
                continue

            class_info = analyze_class(class_node, path)
            all_classes.append(class_info)

    return all_classes


def apply_filters(classes: list[ClassInfo], config: DiagramConfig) -> list[ClassInfo]:
    filtered = []

    for class_info in classes:
        if class_info.name in config.classes_to_skip:
            continue

        if class_info.name.startswith("_"):
            continue

        if (
            config.class_name_filter
            and config.class_name_filter.lower() not in class_info.name.lower()
        ):
            continue

        if (
            config.class_name_exclude
            and config.class_name_exclude.lower() in class_info.name.lower()
        ):
            continue

        filtered.append(class_info)

    return filtered


def include_base_classes(
    classes: list[ClassInfo], all_classes_map: dict[str, ClassInfo]
) -> list[ClassInfo]:
    result = list(classes)
    added_names = {cls.name for cls in classes}

    for class_info in classes:
        for base_class in class_info.base_classes:
            base_class_simple_name = base_class.split(".")[-1]

            if base_class_simple_name not in added_names:
                if base_class_simple_name in all_classes_map:
                    result.append(all_classes_map[base_class_simple_name])
                    added_names.add(base_class_simple_name)

                elif base_class in all_classes_map:
                    result.append(all_classes_map[base_class])
                    added_names.add(base_class)

    return result


def build_diagrams_for_packages(package_paths: list[str], config: DiagramConfig) -> dict[str, str]:
    diagrams = {}

    for package_path in package_paths:
        diagram = build_diagram(package_path, config)
        diagrams[package_path] = diagram

    return diagrams


def filter_inherited_methods(classes: list[ClassInfo]) -> list[ClassInfo]:
    class_methods_map = {cls.name: {method.name for method in cls.methods} for cls in classes}

    class_info_map = {cls.name: cls for cls in classes}

    filtered_classes = []
    for class_info in classes:
        inherited_method_names = get_all_inherited_method_names(
            class_info, class_methods_map, class_info_map
        )

        filtered_methods = [
            method for method in class_info.methods if method.name not in inherited_method_names
        ]

        filtered_class = ClassInfo(
            name=class_info.name,
            module_path=class_info.module_path,
            base_classes=class_info.base_classes,
            methods=filtered_methods,
            attributes=class_info.attributes,
        )
        filtered_classes.append(filtered_class)

    return filtered_classes


def get_all_inherited_method_names(
    class_info: ClassInfo,
    class_methods_map: dict[str, set[str]],
    class_info_map: dict[str, ClassInfo],
    visited: set[str] | None = None,
) -> set[str]:
    if visited is None:
        visited = set()

    inherited_methods = set()

    for base_class in class_info.base_classes:
        base_class_simple_name = base_class.split(".")[-1]

        if base_class_simple_name in visited:
            continue

        visited.add(base_class_simple_name)

        if base_class_simple_name in class_methods_map:
            inherited_methods.update(class_methods_map[base_class_simple_name])

            if base_class_simple_name in class_info_map:
                parent_inherited = get_all_inherited_method_names(
                    class_info_map[base_class_simple_name],
                    class_methods_map,
                    class_info_map,
                    visited,
                )
                inherited_methods.update(parent_inherited)

        if base_class != base_class_simple_name and base_class in class_methods_map:
            inherited_methods.update(class_methods_map[base_class])

            if base_class in class_info_map:
                parent_inherited = get_all_inherited_method_names(
                    class_info_map[base_class], class_methods_map, class_info_map, visited
                )
                inherited_methods.update(parent_inherited)

    return inherited_methods
