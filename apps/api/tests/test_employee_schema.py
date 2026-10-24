"""The employee request models: the vocabulary a directory write accepts and refuses."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from onboarding.api.schemas import EmployeeCreate, EmployeesBulk, EmployeeUpdate


def body(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "employee_id": "1001",
        "name": "Анна Смирнова",
        "role": "Инженер-технолог",
        "department": "Производство",
        "started_at": "2026-10-20",
    }
    base.update(overrides)
    return base


def test_a_minimal_hire_gets_the_deployment_defaults() -> None:
    created = EmployeeCreate.model_validate(body())
    assert created.audience == ["all"]
    assert created.scenario_id == "onboarding_default"
    assert created.recruiter_id is None


@pytest.mark.parametrize("value", ["all", "hr_only", "dept:production", "dept:ИТ"])
def test_the_audience_vocabulary_is_accepted(value: str) -> None:
    assert EmployeeCreate.model_validate(body(audience=[value])).audience == [value]


@pytest.mark.parametrize("value", ["everyone", "dept:", "", "dept:production/../it"])
def test_a_free_form_audience_is_refused(value: str) -> None:
    with pytest.raises(ValidationError):
        EmployeeCreate.model_validate(body(audience=[value]))


def test_a_repeated_audience_entry_is_refused() -> None:
    with pytest.raises(ValidationError):
        EmployeeCreate.model_validate(body(audience=["all", "all"]))


@pytest.mark.parametrize("value", ["", "has space", "a/b"])
def test_the_employee_id_is_an_opaque_token(value: str) -> None:
    with pytest.raises(ValidationError):
        EmployeeCreate.model_validate(body(employee_id=value))


def test_surrounding_whitespace_is_stripped_from_the_id() -> None:
    assert EmployeeCreate.model_validate(body(employee_id=" 1001 ")).employee_id == "1001"


def test_an_unknown_field_fails_instead_of_being_dropped() -> None:
    with pytest.raises(ValidationError):
        EmployeeCreate.model_validate(body(departmnet="Производство"))


def test_a_patch_may_be_empty_and_may_clear_the_recruiter() -> None:
    assert EmployeeUpdate().model_dump(exclude_unset=True) == {}
    cleared = EmployeeUpdate.model_validate({"recruiter_id": None})
    assert cleared.model_dump(exclude_unset=True) == {"recruiter_id": None}


def test_a_patch_cannot_set_the_status_to_left() -> None:
    with pytest.raises(ValidationError):
        EmployeeUpdate.model_validate({"status": "left"})
    assert EmployeeUpdate.model_validate({"status": "active"}).status == "active"


def test_a_batch_keeps_the_order_and_refuses_a_duplicate_id() -> None:
    bulk = EmployeesBulk.model_validate(
        {"employees": [body(employee_id="1"), body(employee_id="2")]}
    )
    assert [row.employee_id for row in bulk.employees] == ["1", "2"]

    with pytest.raises(ValidationError):
        EmployeesBulk.model_validate({"employees": [body(), body()]})


def test_a_batch_is_bounded() -> None:
    with pytest.raises(ValidationError):
        EmployeesBulk.model_validate({"employees": []})
    with pytest.raises(ValidationError):
        EmployeesBulk.model_validate(
            {"employees": [body(employee_id=str(number)) for number in range(501)]}
        )
