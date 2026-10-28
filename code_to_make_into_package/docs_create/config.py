from dataclasses import dataclass, field


@dataclass
class ParameterInfo:
    name: str
    type_hint: str | None
    default_value: str | None


@dataclass
class MethodInfo:
    name: str
    parameters: list[ParameterInfo]
    return_type: str | None
    is_property: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_abstract: bool = False


@dataclass
class ClassInfo:
    name: str
    module_path: str
    base_classes: list[str]
    methods: list[MethodInfo]
    attributes: list[tuple[str, str | None]] = field(default_factory=list)


@dataclass
class DiagramConfig:
    package_paths: list[str]
    output_folder: str = "./docs/graphs/"
    classes_to_skip: list[str] = field(default_factory=list)
    class_name_filter: str | None = None
    class_name_exclude: str | None = None
    include_private_methods: bool = False
    include_properties: bool = True
    include_class_methods: bool = True
    include_static_methods: bool = True
    include_abstract_methods: bool = True
    max_method_count: int = 20
    include_attributes: bool = True
