from pathlib import Path

from tai.docs_create.config import DiagramConfig
from tai.docs_create.diagram_builder import build_diagram


def main() -> None:
    generate_zones_diagram()
    generate_effectors_diagram()
    generate_events_diagram()
    generate_targets_diagram()
    generate_world_diagram()


def generate_zones_diagram() -> None:
    config = create_config(
        package_path="src/tai/geometry/zones",
        class_name_filter="zone",
    )
    diagram = build_diagram(config.package_paths[0], config)
    save_diagram(diagram, "docs/graphs/zones.md")


def generate_effectors_diagram() -> None:
    config = create_config(
        package_path="src/tai/world/effectors",
        class_name_filter="effector",
    )
    diagram = build_diagram(config.package_paths[0], config)
    save_diagram(diagram, "docs/graphs/effectors.md")


def generate_events_diagram() -> None:
    config = create_config(
        package_path="src/tai/world/events",
        class_name_filter="event",
    )
    diagram = build_diagram(config.package_paths[0], config)
    save_diagram(diagram, "docs/graphs/events.md")


def generate_targets_diagram() -> None:
    config = create_config(
        package_path="src/tai",
        class_name_filter="target",
        class_name_exclude="event",
    )
    diagram = build_diagram(config.package_paths[0], config)
    save_diagram(diagram, "docs/graphs/target.md")


def generate_world_diagram() -> None:
    config = create_config(
        package_path="src/tai/world",
        class_name_filter="world",
    )
    diagram = build_diagram(config.package_paths[0], config)
    save_diagram(diagram, "docs/graphs/world.md")


def create_config(
    package_path: str, class_name_filter: str, class_name_exclude: str | None = None
) -> DiagramConfig:
    return DiagramConfig(
        package_paths=[package_path],
        output_folder="./docs/graphs/",
        classes_to_skip=["TestCase", "ABC", "BaseModel", "Enum", "StrictBaseModel"],
        class_name_filter=class_name_filter,
        class_name_exclude=class_name_exclude,
        include_private_methods=False,
        include_properties=True,
        include_class_methods=True,
        include_static_methods=True,
        include_abstract_methods=True,
        max_method_count=15,
        include_attributes=True,
    )


def save_diagram(diagram: str, output_path: str) -> None:
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    content = f"```mermaid\n{diagram}\n```\n"
    output_file.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
