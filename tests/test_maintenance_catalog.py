"""Maintenance catalogue and the per-task-type execution policies."""

import pytest

from desalplant.maintenance.catalog import Catalog, TaskDef, TaskType
from desalplant.maintenance.policy import ExecutionPolicy, WindowRequirement


def test_default_catalogue_covers_the_three_families():
    catalog = Catalog()
    by_type = {str(task.type): task for task in catalog.types()}
    assert {str(t) for t in TaskType} == set(by_type)
    rinse = by_type["screen-rinse"]
    backwash = by_type["media-backwash"]
    dose = by_type["dose-check"]
    assert rinse.label == "格栅冲洗"
    assert backwash.label == "反洗"
    assert dose.label == "加药"
    # Every family keeps its own interval and lead time.
    assert rinse.interval != backwash.interval != dose.interval
    assert all(task.lead >= 0 for task in catalog.types())


def test_window_and_preemption_are_fixed_by_type():
    catalog = Catalog()
    rinse = catalog.get(TaskType.SCREEN_RINSE)
    backwash = catalog.get(TaskType.MEDIA_BACKWASH)
    dose = catalog.get(TaskType.DOSE_CHECK)
    # The screen rinse is safe under production and may overtake the queue;
    # the backwash and dosing check always wait for a shutdown window.
    assert rinse.policy.window is WindowRequirement.RUNNING
    assert rinse.policy.preemptive is True
    assert backwash.policy.requires_stop is True
    assert backwash.policy.preemptive is False
    assert dose.policy.requires_stop is True
    assert dose.policy.preemptive is False


def test_preemption_only_applies_to_a_queued_other_task():
    pre = ExecutionPolicy(WindowRequirement.RUNNING, preemptive=True)
    plain = ExecutionPolicy(WindowRequirement.STOPPED, preemptive=False)
    assert pre.may_preempt(plain) is True
    assert plain.may_preempt(pre) is False
    # Even a preemptive type never overtake another preemptive one.
    assert pre.may_preempt(pre) is False


def test_task_definition_validates_its_numbers():
    with pytest.raises(ValueError):
        TaskDef(TaskType.SCREEN_RINSE, "x", interval=0, lead=0, priority=1,
                policy=ExecutionPolicy(WindowRequirement.RUNNING))
    with pytest.raises(ValueError):
        TaskDef(TaskType.SCREEN_RINSE, "x", interval=10, lead=-1, priority=1,
                policy=ExecutionPolicy(WindowRequirement.RUNNING))
    with pytest.raises(ValueError):
        TaskDef(TaskType.SCREEN_RINSE, "x", interval=10, lead=0, priority=0,
                policy=ExecutionPolicy(WindowRequirement.RUNNING))


def test_catalog_lookup_and_duplicate_rejection():
    catalog = Catalog()
    assert catalog.has("dose-check")
    assert catalog.has("nope") is False
    assert catalog.get("dose-check").type is TaskType.DOSE_CHECK
    with pytest.raises(KeyError):
        catalog.get("nope")
    duplicate = (
        TaskDef(TaskType.SCREEN_RINSE, "格栅冲洗", 1, 0, 1,
                ExecutionPolicy(WindowRequirement.RUNNING)),
        TaskDef(TaskType.SCREEN_RINSE, "格栅冲洗二", 2, 0, 1,
                ExecutionPolicy(WindowRequirement.RUNNING)),
    )
    with pytest.raises(ValueError):
        Catalog(duplicate)
