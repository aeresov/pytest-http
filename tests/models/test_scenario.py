import pytest
from pydantic import ValidationError

from pytest_http.models import Scenario


def test_scenario_with_stages():
    data = {"stages": [{"name": "stage1", "data": "data1"}, {"name": "stage2", "data": 42}]}
    scenario = Scenario.model_validate(data)
    assert len(scenario.stages) == 2
    assert scenario.stages[0].name == "stage1"
    assert scenario.stages[0].data == "data1"
    assert scenario.stages[1].name == "stage2"
    assert scenario.stages[1].data == 42


def test_scenario_empty():
    data = {}
    scenario = Scenario.model_validate(data)
    assert scenario.stages == []


def test_scenario_empty_stages():
    data = {"stages": []}
    scenario = Scenario.model_validate(data)
    assert scenario.stages == []


def test_scenario_with_extra_fields():
    data = {"stages": [{"name": "test", "data": 123}], "unknown_field": "should_be_ignored"}
    scenario = Scenario.model_validate(data)
    assert len(scenario.stages) == 1
    assert not hasattr(scenario, "unknown_field")


def test_scenario_invalid_stages_type():
    data = {"stages": "not_a_list"}
    with pytest.raises(ValidationError):
        Scenario.model_validate(data)


def test_scenario_invalid_stage_structure():
    data = {"stages": [{"name": "valid_stage", "data": "data"}, {"invalid": "stage"}]}
    with pytest.raises(ValidationError):
        Scenario.model_validate(data)


def test_scenario_with_complex_stages():
    data = {
        "stages": [
            {"name": "setup", "data": {"config": {"host": "localhost", "port": 8080}, "users": ["alice", "bob"]}},
            {"name": "action", "data": ["step1", "step2", "step3"]},
            {"name": "verification", "data": True},
        ]
    }
    scenario = Scenario.model_validate(data)
    assert len(scenario.stages) == 3
    assert scenario.stages[0].name == "setup"
    assert scenario.stages[0].data["config"]["host"] == "localhost"
    assert scenario.stages[1].data == ["step1", "step2", "step3"]
    assert scenario.stages[2].data is True
