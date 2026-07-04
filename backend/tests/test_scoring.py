from app.guardrails.scoring import validate_score


def test_valid_score():
    assert validate_score(78, 72)


def test_invalid_score():
    assert not validate_score(120, 72)
