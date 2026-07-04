def validate_score(score: int, confidence: int) -> bool:
    return 0 <= score <= 100 and 0 <= confidence <= 100
