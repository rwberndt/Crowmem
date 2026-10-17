from app.services import risk_service
from app.services.salience_service import SalienceSignals, classify_salience, compute_salience, should_encode

THRESHOLDS = {"discard": 0.25, "candidate": 0.60, "durable": 0.85}
WEIGHTS = {
    "novelty": 0.20,
    "future_utility": 0.20,
    "task_relevance": 0.20,
    "risk": 0.15,
    "surprise": 0.10,
    "decision_importance": 0.10,
    "user_correction": 0.05,
}


def test_compute_salience_is_weighted_sum():
    signals = SalienceSignals(
        novelty=1.0, future_utility=1.0, task_relevance=1.0, risk=1.0, surprise=1.0, decision_importance=1.0, user_correction=1.0
    )
    assert compute_salience(signals, WEIGHTS) == 1.0

    zero_signals = SalienceSignals(0, 0, 0, 0, 0, 0, 0)
    assert compute_salience(zero_signals, WEIGHTS) == 0.0


def test_low_salience_event_is_discarded():
    # "Opened README" -- guide section 6/8 example of a low-salience event.
    signals = SalienceSignals(
        novelty=0.1, future_utility=0.05, task_relevance=0.1, risk=0.0, surprise=0.2, decision_importance=0.0, user_correction=0.0
    )
    score = compute_salience(signals, WEIGHTS)
    assert score < THRESHOLDS["discard"]
    assert classify_salience(score, THRESHOLDS) == "discard"
    assert should_encode(score, THRESHOLDS) is False


def test_high_salience_production_failure_is_encoded():
    # "Production migration failed" -- guide section 6 example of very high salience.
    signals = SalienceSignals(
        novelty=0.8, future_utility=0.9, task_relevance=0.9, risk=0.95, surprise=0.85, decision_importance=0.6, user_correction=0.0
    )
    score = compute_salience(signals, WEIGHTS)
    assert score >= THRESHOLDS["candidate"]
    assert should_encode(score, THRESHOLDS) is True


def test_risk_service_flags_production_destructive_commands():
    risk = risk_service.compute_risk(
        "Running prisma migrate dev failed because production contains existing migrations.",
        {"environment": "production", "tool": "prisma"},
    )
    assert risk >= 0.8


def test_risk_service_low_for_benign_content():
    risk = risk_service.compute_risk("Opened README.md to check project description.", {})
    assert risk == 0.0


def test_user_correction_signal_is_binary():
    assert risk_service.compute_user_correction("user_correction") == 1.0
    assert risk_service.compute_user_correction("tool_success") == 0.0


def test_task_relevance_rises_with_metadata_specificity():
    bare = risk_service.compute_task_relevance({})
    specific = risk_service.compute_task_relevance(
        {"environment": "production", "tool": "prisma", "task": "database_migration", "project": "peach"}
    )
    assert specific > bare


def test_code_change_has_enough_future_utility_to_reach_extraction_gate():
    assert risk_service.compute_future_utility("Changed path resolution", "code_change", {"tool": "Edit"}) >= 0.6
