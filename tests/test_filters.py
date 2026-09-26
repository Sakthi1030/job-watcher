import yaml
from pathlib import Path

import pytest

from job_watcher.filters import Filters, min_years

PROFILE = yaml.safe_load((Path(__file__).parent.parent / "config" / "profile.yaml").read_text())


@pytest.mark.parametrize("text, expected", [
    ("Required: 1 to 2 years of professional software development experience.", 1),
    ("3-7 years of experience in Data Analytics. Minimum 2 years of hands-on Fabric.", 3),
    ("Experience: 5-8 Years", 5),
    ("Minimum experience of 1.5 - 2 years and above in operations", 1),
    ("No experience requirement mentioned.", None),
    ("Founded 150 years ago. 4+ years experience with Power BI.", 4),
    ("Demonstrate proven architecture experience of at least ten years", 10),
])
def test_min_years(text, expected):
    assert min_years(text) == expected


@pytest.mark.parametrize("title, ok", [
    ("Power BI Developer", True),
    ("Data Engineer with experience to Python, Airflow, Databricks & SQL", True),
    ("Associate, Analytics and Insights", True),
    ("Senior Data Engineer", False),
    ("Lead - Power BI", False),
    ("Microsoft Fabric Architect", False),
    ("Java Full Stack Developer", False),
])
def test_title_filter(title, ok):
    assert Filters(PROFILE).title_ok(title) is ok


def test_location_and_experience():
    f = Filters(PROFILE)
    assert f.location_ok("Hyderabad, Telangana, India")
    assert not f.location_ok("Austin, Texas, United States")
    assert f.experience_ok(None) and f.experience_ok(3) and not f.experience_ok(5)
