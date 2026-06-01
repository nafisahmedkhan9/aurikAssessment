import pytest
from datetime import datetime, timezone
from app.services.normalization import parse_iso_time, fahrenheit_to_celsius, map_pulseforge_severity
from app.models.domain import SeverityLevel

def test_parse_iso_time():
    dt = parse_iso_time("2026-04-18T07:59:12Z")
    assert dt.year == 2026
    assert dt.month == 4
    assert dt.day == 18
    assert dt.hour == 7
    assert dt.minute == 59
    assert dt.second == 12
    assert dt.tzinfo is not None

def test_fahrenheit_to_celsius():
    assert fahrenheit_to_celsius(32.0) == 0.0
    assert fahrenheit_to_celsius(212.0) == 100.0
    assert round(fahrenheit_to_celsius(181.2), 1) == 82.9

def test_map_pulseforge_severity():
    assert map_pulseforge_severity("nominal") == SeverityLevel.NOMINAL
    assert map_pulseforge_severity("critical") == SeverityLevel.CRITICAL
    assert map_pulseforge_severity("UNKNOWN_STRING") == SeverityLevel.NOMINAL
