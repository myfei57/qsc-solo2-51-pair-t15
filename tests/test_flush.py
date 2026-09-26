"""Membrane flush: stages, plan validation, program and stop gate."""

import pytest

from desalplant.errors import FlushNotEffectiveError, PumpAlreadyStoppedError
from desalplant.flush.control import Program, program
from desalplant.flush.history import History
from desalplant.flush.rinse import RinseCycle
from desalplant.flush.stage import Stage, plan
from desalplant.flush.start import Flusher, StopGate
from desalplant.flush.validator import valid

STAGES = (
    Stage(name="pre-rinse", seconds=15),
    Stage(name="chemical-rinse", seconds=20),
    Stage(name="post-rinse", seconds=15),
)


def test_stage_projection_and_plan_totals():
    assert STAGES[0].to_dict() == {"name": "pre-rinse", "seconds": 15}
    flush_plan = plan(STAGES)
    assert flush_plan.total_seconds() == 50
    assert flush_plan.names() == ("pre-rinse", "chemical-rinse", "post-rinse")
    assert flush_plan.valid() is True


def test_plan_validation_rejects_bad_stages():
    assert valid(plan([])) is False
    assert valid(plan([Stage(name="", seconds=10)])) is False
    assert valid(plan([Stage(name="rinse", seconds=0)])) is False


def test_program_advances_and_completes():
    cursor = program(STAGES)
    assert isinstance(cursor, Program)
    assert cursor.remaining() == 3
    assert cursor.advance() is True
    assert cursor.remaining() == 2
    cursor.advance()
    cursor.advance()
    assert cursor.complete() is True
    assert cursor.advance() is False
    assert cursor.remaining() == 0


def test_program_can_be_built_without_a_stage_list():
    assert Program().complete() is True


def test_flusher_only_takes_effect_with_a_running_pump():
    flusher = Flusher()
    assert flusher.start(True) is True
    assert flusher.started is True
    assert flusher.effective is True
    assert Flusher().start(False) is False


def test_flusher_reports_missing_flush_water():
    flusher = Flusher(available=False)
    assert flusher.start(True) is False
    assert flusher.started is True
    assert flusher.effective is False


def test_stop_gate_flushes_before_stopping():
    flusher = Flusher()
    StopGate(True).flush(flusher)
    assert flusher.started is True
    assert flusher.effective is True


def test_stop_gate_refuses_a_stopped_pump():
    with pytest.raises(PumpAlreadyStoppedError):
        StopGate(False).flush(Flusher())
    with pytest.raises(FlushNotEffectiveError):
        StopGate(True).flush(Flusher(available=False))


def test_flush_history_averages():
    history = History()
    assert history.average_seconds() == 0.0
    assert history.record(plan(STAGES)) == 50
    assert history.runs == 1
    assert history.average_seconds() == 50.0


def test_rinse_cycle_runs_once():
    cycle = RinseCycle()
    assert cycle.done is False
    assert cycle.run() is True
    assert cycle.done is True
