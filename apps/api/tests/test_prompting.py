from __future__ import annotations

import pytest

from onboarding.core.prompting import PromptError, placeholders, render


def test_renders_every_placeholder() -> None:
    template = "Имя: {{employee_name}}. Отдел: {{ department }}."

    assert render(template, {"employee_name": "Иван", "department": "ИТ"}) == (
        "Имя: Иван. Отдел: ИТ."
    )


def test_missing_value_is_an_error() -> None:
    with pytest.raises(PromptError, match="missing"):
        render("Привет, {{name}}", {})


def test_unused_value_is_an_error() -> None:
    with pytest.raises(PromptError, match="unused"):
        render("Привет", {"name": "Иван"})


def test_placeholders_are_listed_in_order() -> None:
    assert placeholders("{{a}} {{b}} {{a}}") == ("a", "b", "a")
