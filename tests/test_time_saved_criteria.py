"""Minutes saved per email use case (azure/weekly_analytics.py), as agreed: UC1 20, UC2 10,
UC3 90, UC4 15. The business impact report and the deck are built on these values."""
import weekly_analytics as wa


def test_minutes_per_use_case():
    assert wa.MINUTES == {"UC1": 20, "UC4": 15, "UC2": 10, "UC3": 90}
