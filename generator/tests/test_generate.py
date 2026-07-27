"""Minimal test to verify dependency injection in generate_project()."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_generate_with_mock_validator():
    """Verify that generate_project accepts and uses an injected validator."""
    from generate import generate_project

    # Track that mock was called
    called_validator = []
    called_loader = []

    def mock_validate(hw):
        called_validator.append(True)
        return [{"severity": "ERROR", "message": "Mock validation error"}]

    def mock_load(path):
        called_loader.append(path)
        return {"mcu": {"part": "STM32G0B1RET6"}, "peripherals": []}

    def mock_build(hw, name, hil=False):
        return {"project_name": name, "mcu": {}}

    try:
        generate_project(
            yaml_path="dummy.yaml",
            output_dir="/tmp/test_output_mock",
            validate_fn=mock_validate,
            build_context_fn=mock_build,
            load_yaml_fn=mock_load,
        )
    except SystemExit:
        pass

    assert len(called_loader) == 1, "Mock loader was not called"
    assert len(called_validator) == 1, "Mock validator was not called"


def test_generate_with_mock_context_builder():
    """Verify that generate_project accepts and uses an injected context builder."""
    from generate import generate_project

    called_builder = []

    def mock_validate(hw):
        return []  # no errors, proceed to context building

    def mock_load(path):
        return {"mcu": {"part": "STM32G0B1RET6"}, "peripherals": []}

    def mock_build(hw, name, hil=False):
        called_builder.append((name, hil))
        # Return empty context that will cause template rendering to fail,
        # but we only care that the builder was called.
        return {}

    # Template rendering will fail with empty context, expect SystemExit or exception
    try:
        generate_project(
            yaml_path="dummy.yaml",
            output_dir="/tmp/test_output_mock",
            validate_fn=mock_validate,
            build_context_fn=mock_build,
            load_yaml_fn=mock_load,
        )
    except (SystemExit, Exception):
        pass

    assert len(called_builder) == 1, "Mock context builder was not called"
    assert called_builder[0] == ("test_output_mock", False), \
        f"Expected ('test_output_mock', False), got {called_builder[0]}"


if __name__ == "__main__":
    test_generate_with_mock_validator()
    test_generate_with_mock_context_builder()
    print("All tests passed.")
