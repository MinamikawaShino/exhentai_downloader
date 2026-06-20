import pytest
from src.cli import format_time

def test_format_time_seconds():
    assert format_time(0) == "0s"
    assert format_time(59) == "59s"

def test_format_time_minutes():
    assert format_time(60) == "1m 0s"
    assert format_time(61) == "1m 1s"
    assert format_time(3599) == "59m 59s"

def test_format_time_hours():
    assert format_time(3600) == "1h 0m"
    assert format_time(3661) == "1h 1m"
    assert format_time(7200) == "2h 0m"
