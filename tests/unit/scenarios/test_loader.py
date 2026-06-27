from pathlib import Path

import pytest

from watch_ui_automation.actions.registry import ActionRegistry
from watch_ui_automation.scenarios.errors import ScenarioSchemaError
from watch_ui_automation.scenarios.loader import load_scenarios


def make_registry() -> ActionRegistry:
    registry = ActionRegistry()
    registry.register("capture.current_page", lambda ctx: {"name": "main"})
    registry.register("assert.equals", lambda ctx, **params: None)
    return registry


def write_yaml(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_load_scenarios_reads_valid_yaml_cases(tmp_path: Path) -> None:
    scenario_file = write_yaml(
        tmp_path / "widget.yaml",
        """
cases:
  - id: smoke_widget
    title: Smoke widget
    markers: [yaml, device, smoke]
    baseline: main
    steps:
      - name: capture page
        action: capture.current_page
        save_as: current_page
      - name: assert page
        action: assert.equals
        params:
          actual: ${current_page.name}
          expected: main
""",
    )

    cases = load_scenarios(tmp_path, registry=make_registry())

    assert len(cases) == 1
    assert cases[0].id == "smoke_widget"
    assert cases[0].source_file == str(scenario_file)
    assert cases[0].steps[0].save_as == "current_page"


def test_load_scenarios_rejects_unknown_action(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: bad_case
    title: Bad case
    markers: [yaml]
    baseline: main
    steps:
      - name: missing
        action: missing.action
""",
    )

    with pytest.raises(ScenarioSchemaError) as exc_info:
        load_scenarios(tmp_path, registry=make_registry())

    message = str(exc_info.value)
    assert "Unknown action 'missing.action'" in message
    assert "case=bad_case" in message
    assert "step=missing" in message


def test_load_scenarios_rejects_empty_scenario_dir(tmp_path: Path) -> None:
    with pytest.raises(ScenarioSchemaError, match="No scenario YAML files found"):
        load_scenarios(tmp_path, registry=make_registry())


def test_load_scenarios_wraps_invalid_yaml_syntax(tmp_path: Path) -> None:
    scenario_file = write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: broken
    title: Broken
    markers: [yaml
""",
    )

    with pytest.raises(ScenarioSchemaError) as exc_info:
        load_scenarios(tmp_path, registry=make_registry())

    message = str(exc_info.value)
    assert "Invalid YAML" in message
    assert str(scenario_file) in message


def test_load_scenarios_rejects_unknown_marker(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: bad_case
    title: Bad case
    markers: [yaml, unsafe]
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
""",
    )

    with pytest.raises(ScenarioSchemaError, match="Unknown marker 'unsafe'"):
        load_scenarios(tmp_path, registry=make_registry())


def test_load_scenarios_rejects_unknown_top_level_field(tmp_path: Path) -> None:
    scenario_file = write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: bad_case
    title: Bad case
    markers: [yaml]
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
defaults: {}
""",
    )

    with pytest.raises(ScenarioSchemaError) as exc_info:
        load_scenarios(tmp_path, registry=make_registry())

    message = str(exc_info.value)
    assert "Unknown field 'defaults'" in message
    assert str(scenario_file) in message


def test_load_scenarios_rejects_unknown_case_field(tmp_path: Path) -> None:
    scenario_file = write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: bad_case
    title: Bad case
    markers: [yaml]
    marker: smoke
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
""",
    )

    with pytest.raises(ScenarioSchemaError) as exc_info:
        load_scenarios(tmp_path, registry=make_registry())

    message = str(exc_info.value)
    assert "Unknown field 'marker'" in message
    assert str(scenario_file) in message
    assert "case=bad_case" in message


def test_load_scenarios_rejects_unknown_step_field(tmp_path: Path) -> None:
    scenario_file = write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: bad_case
    title: Bad case
    markers: [yaml]
    baseline: main
    steps:
      - name: assert page
        action: assert.equals
        param:
          actual: main
          expected: main
""",
    )

    with pytest.raises(ScenarioSchemaError) as exc_info:
        load_scenarios(tmp_path, registry=make_registry())

    message = str(exc_info.value)
    assert "Unknown field 'param'" in message
    assert str(scenario_file) in message
    assert "case=bad_case" in message
    assert "step=assert page" in message


def test_load_scenarios_rejects_missing_markers(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: bad_case
    title: Bad case
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
""",
    )

    with pytest.raises(ScenarioSchemaError, match="'markers' must be a string list"):
        load_scenarios(tmp_path, registry=make_registry())


def test_load_scenarios_rejects_forward_variable_reference(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: bad_case
    title: Bad case
    markers: [yaml]
    baseline: main
    steps:
      - name: assert first
        action: assert.equals
        params:
          actual: ${captured.name}
          expected: main
      - name: capture later
        action: capture.current_page
        save_as: captured
""",
    )

    with pytest.raises(ScenarioSchemaError, match="Undefined variable 'captured'"):
        load_scenarios(tmp_path, registry=make_registry())


def test_load_scenarios_rejects_invalid_variable_reference_expression(
    tmp_path: Path,
) -> None:
    write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: bad_case
    title: Bad case
    markers: [yaml]
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
        save_as: captured
      - name: assert expression
        action: assert.equals
        params:
          actual: ${captured.name == "main"}
          expected: main
""",
    )

    with pytest.raises(ScenarioSchemaError, match="Invalid variable reference"):
        load_scenarios(tmp_path, registry=make_registry())


def test_load_scenarios_rejects_invalid_variable_reference_path(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: bad_case
    title: Bad case
    markers: [yaml]
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
        save_as: captured
      - name: assert path
        action: assert.equals
        params:
          actual: ${captured.}
          expected: main
""",
    )

    with pytest.raises(ScenarioSchemaError, match="Invalid variable reference"):
        load_scenarios(tmp_path, registry=make_registry())


def test_load_scenarios_rejects_embedded_variable_reference(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: bad_case
    title: Bad case
    markers: [yaml]
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
        save_as: captured
      - name: assert embedded
        action: assert.equals
        params:
          actual: page is ${captured.name}
          expected: main
""",
    )

    with pytest.raises(ScenarioSchemaError, match="Variable reference must occupy"):
        load_scenarios(tmp_path, registry=make_registry())


def test_load_scenarios_rejects_unclosed_variable_reference(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: bad_case
    title: Bad case
    markers: [yaml]
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
        save_as: captured
      - name: assert unclosed
        action: assert.equals
        params:
          actual: ${captured.name
          expected: main
""",
    )

    with pytest.raises(ScenarioSchemaError, match="Invalid variable reference syntax"):
        load_scenarios(tmp_path, registry=make_registry())


def test_load_scenarios_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: duplicate
    title: First
    markers: [yaml]
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
  - id: duplicate
    title: Second
    markers: [yaml]
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
""",
    )

    with pytest.raises(ScenarioSchemaError, match="Duplicate case id 'duplicate'"):
        load_scenarios(tmp_path, registry=make_registry())


def test_load_scenarios_rejects_duplicate_case_ids_across_files(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "a.yaml",
        """
cases:
  - id: duplicate
    title: First
    markers: [yaml]
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
""",
    )
    write_yaml(
        tmp_path / "b.yaml",
        """
cases:
  - id: duplicate
    title: Second
    markers: [yaml]
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
""",
    )

    with pytest.raises(ScenarioSchemaError, match="Duplicate case id 'duplicate'"):
        load_scenarios(tmp_path, registry=make_registry())


def test_load_scenarios_rejects_duplicate_save_as(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "bad.yaml",
        """
cases:
  - id: duplicate_save
    title: Duplicate save
    markers: [yaml]
    baseline: main
    steps:
      - name: capture
        action: capture.current_page
        save_as: captured
      - name: capture again
        action: capture.current_page
        save_as: captured
""",
    )

    with pytest.raises(ScenarioSchemaError, match="Duplicate save_as 'captured'"):
        load_scenarios(tmp_path, registry=make_registry())
