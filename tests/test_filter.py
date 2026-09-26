"""Multi-media filtration: media bed, rack, backwash and age."""

import pytest

from desalplant.errors import MediaNotReadyError
from desalplant.filter.age import MediaAge
from desalplant.filter.backwash import finish_backwash, start_backwash
from desalplant.filter.control import BackwashSchedule, schedule
from desalplant.filter.history import BackwashHistory
from desalplant.filter.media import MediaFilter
from desalplant.filter.rack import Rack


def test_media_filter_backwash_gates_readiness():
    bed = MediaFilter()
    assert bed.ready() is False
    with pytest.raises(MediaNotReadyError):
        bed.require_ready()
    bed.backwash()
    bed.require_ready()
    assert bed.ready() is True


def test_media_filter_head_loss_depends_on_backwash():
    bed = MediaFilter()
    assert bed.pressure_drop(0.0) == 0.0
    dirty = bed.pressure_drop(80.0)
    bed.backwash()
    clean = bed.pressure_drop(80.0)
    assert dirty > clean
    assert bed.needs_backwash(dirty, 20.0) is True
    assert bed.needs_backwash(clean, 20.0) is False
    assert MediaFilter().needs_backwash(0.0, 20.0) is True


def test_backwash_cycle_start_and_finish():
    bed = MediaFilter()
    cycle = start_backwash(bed, 80.0)
    assert cycle.completed is False
    assert cycle.pressure_drop > 0
    done = finish_backwash(bed)
    assert done.completed is True
    assert done.to_dict() == {"completed": True, "pressure_drop": 0.0}


def test_backwash_schedule_due():
    backwash_schedule = schedule(100)
    assert isinstance(backwash_schedule, BackwashSchedule)
    assert backwash_schedule.due(200) is False
    assert backwash_schedule.due(400) is True


def test_backwash_history_summarises_drops():
    history = BackwashHistory()
    assert history.average_drop() == 0.0
    assert history.worst_drop() == 0.0
    history.record(12.0)
    history.record(18.0)
    assert history.runs == 2
    assert history.average_drop() == 15.0
    assert history.worst_drop() == 18.0


def test_rack_rinse_tracks_blockage():
    rack = Rack()
    assert rack.rinse(True) is True
    assert rack.was_rinsed() is True
    assert rack.blocked is False
    assert rack.inspect().growth_score == 0.0


def test_rack_rinse_with_a_stopped_pump_blocks_it():
    rack = Rack()
    assert rack.rinse(False) is False
    state = rack.inspect()
    assert state.blocked is True
    assert state.growth_score == 135.0
    rack.clean()
    assert rack.inspect().growth_score == 0.0


def test_rack_never_rinsed_scores_growth():
    rack = Rack()
    assert rack.inspect().growth_score == 35.0


def test_jammed_rack_refuses_to_rinse():
    rack = Rack(jammed=True)
    assert rack.rinse(True) is False
    assert rack.was_rinsed() is False
    assert rack.inspect().blocked is True


def test_media_age_expiry_and_remaining():
    age = MediaAge(days=90, limit=120)
    assert age.expired() is False
    assert age.remaining() == 30
    assert MediaAge(days=120, limit=120).expired() is True
    assert MediaAge(days=200, limit=120).remaining() == 0
