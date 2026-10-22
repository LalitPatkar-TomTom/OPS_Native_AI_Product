"""Which use cases run in which slot (fire_all_now.py). Azure runs at 09:00, 13:00, 17:00 and
21:00 IST: UC1 in the morning slot, UC2 and UC4 every slot, UC3 on Friday from 17:00."""
from datetime import datetime

import pytest
import pytz

import fire_all_now as f

IST = pytz.timezone("Asia/Kolkata")


@pytest.mark.parametrize("hour,weekday,expected", [
    (9, 0, ["UC1", "UC2", "UC4"]), (13, 0, ["UC2", "UC4"]), (17, 3, ["UC2", "UC4"]),
    (17, 4, ["UC2", "UC4", "UC3"]), (21, 4, ["UC2", "UC4", "UC3"]), (9, 5, ["UC1", "UC2", "UC4"])])
def test_use_cases_per_slot(hour, weekday, expected):
    assert f._which_ucs(hour, weekday) == expected


@pytest.mark.parametrize("hh,mm,expected", [
    (9, 7, ("2026-10-23", "09:00", 7)), (12, 0, ("2026-10-23", "09:00", 180)),
    (8, 59, ("2026-10-22", "21:00", 719)), (21, 30, ("2026-10-23", "21:00", 30))])
def test_slot_served_and_delay(hh, mm, expected):
    assert f._slot_for(IST.localize(datetime(2026, 10, 23, hh, mm))) == expected
