import pytest

from app.github.parser import parse_pr_url


def test_parse_valid_pr_url():
    result = parse_pr_url("https://github.com/openai/openai-python/pull/123")

    assert result.owner == "openai"
    assert result.repo == "openai-python"
    assert result.pr_number == 123


def test_parse_invalid_pr_url():
    with pytest.raises(ValueError):
        parse_pr_url("https://github.com/openai/openai-python/issues/123")
