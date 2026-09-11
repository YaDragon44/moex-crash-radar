from dataclasses import dataclass

from moex_crash_radar.crowd_transition import stable_states


@dataclass
class Row:
    day: str
    score: float
    state: str


def rows(scores_states):
    return [Row(f"2026-01-{i+1:02d}", score, state) for i, (score, state) in enumerate(scores_states)]


def test_single_day_flip_does_not_change_stable_state():
    data = rows([(65,"GREED"),(66,"GREED"),(67,"GREED"),(58,"NEUTRAL"),(66,"GREED")])
    result = stable_states(data, persistence=3)
    assert result[2].stable_state == "GREED"
    assert result[-1].stable_state == "GREED"


def test_persistent_deterioration_changes_state():
    data = rows([(70,"GREED"),(71,"GREED"),(72,"GREED"),(50,"NEUTRAL"),(49,"NEUTRAL"),(48,"NEUTRAL")])
    result = stable_states(data, persistence=3)
    assert result[2].stable_state == "GREED"
    assert result[-1].stable_state == "NEUTRAL"


def test_falling_fast_uses_five_session_delta():
    data = rows([(75,"GREED"),(72,"GREED"),(68,"GREED"),(64,"GREED"),(61,"GREED"),(55,"NEUTRAL")])
    result = stable_states(data, persistence=3)
    assert result[-1].delta_5 == -20
    assert result[-1].falling_fast is True
