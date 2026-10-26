"""Minutes saved per email use case (azure/weekly_analytics.py), from real-user feedback on 26 Oct: UC1, UC2 and
UC4 25, UC3 60. The business impact report and the deck are built on these values."""
import weekly_analytics as wa


def test_minutes_per_use_case():
    assert wa.MINUTES == {"UC1": 25, "UC4": 25, "UC2": 25, "UC3": 60}
