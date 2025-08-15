from datetime import timedelta
from django.test import TestCase

from tally_ho.libs.utils.time import format_duration_human_readable


class TestTimeUtils(TestCase):
    def test_format_duration_none(self):
        """Test None input returns None"""
        result = format_duration_human_readable(None)
        self.assertIsNone(result)

    def test_format_duration_zero_seconds(self):
        """Test zero duration"""
        duration = timedelta(seconds=0)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "0s")

    def test_format_duration_seconds_only(self):
        """Test seconds formatting"""
        duration = timedelta(seconds=30)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "30s")

    def test_format_duration_exactly_one_minute(self):
        """Test exactly 60 seconds"""
        duration = timedelta(seconds=60)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "1m")

    def test_format_duration_minutes_only(self):
        """Test minutes formatting"""
        duration = timedelta(minutes=45)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "45m")

    def test_format_duration_minutes_and_seconds(self):
        """Test minutes with remaining seconds"""
        duration = timedelta(minutes=2, seconds=30)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "2m")  # Seconds are ignored when minutes exist

    def test_format_duration_exactly_one_hour(self):
        """Test exactly one hour"""
        duration = timedelta(hours=1)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "1h 0m")

    def test_format_duration_hours_and_minutes(self):
        """Test hours and minutes formatting"""
        duration = timedelta(hours=1, minutes=30)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "1h 30m")

    def test_format_duration_hours_minutes_seconds(self):
        """Test hours with minutes and seconds"""
        duration = timedelta(hours=2, minutes=15, seconds=45)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "2h 15m")  # Seconds ignored when hours exist

    def test_format_duration_exactly_one_day(self):
        """Test exactly one day"""
        duration = timedelta(days=1)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "1d 0h 0m")

    def test_format_duration_days_hours_minutes(self):
        """Test days, hours, and minutes formatting"""
        duration = timedelta(days=2, hours=1, minutes=3)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "2d 1h 3m")

    def test_format_duration_days_with_seconds(self):
        """Test days with all time units"""
        duration = timedelta(days=1, hours=2, minutes=30, seconds=45)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "1d 2h 30m")  # Seconds ignored when days exist

    def test_format_duration_large_values(self):
        """Test large duration values"""
        # 49 hours = 2 days and 1 hour
        duration = timedelta(hours=49, minutes=3)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "2d 1h 3m")

    def test_format_duration_fractional_seconds(self):
        """Test fractional seconds are handled correctly"""
        duration = timedelta(seconds=30.7)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "30s")  # Should truncate to integer

    def test_format_duration_edge_case_23_hours_59_minutes(self):
        """Test edge case just under 1 day"""
        duration = timedelta(hours=23, minutes=59, seconds=59)
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "23h 59m")

    def test_format_duration_microseconds(self):
        """Test microseconds are handled"""
        duration = timedelta(microseconds=500000)  # 0.5 seconds
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "0s")  # Should round down

    def test_format_duration_real_world_example(self):
        """Test real-world duration like 2943 minutes"""
        duration = timedelta(minutes=2943)  # Should be 2d 1h 3m
        result = format_duration_human_readable(duration)
        self.assertEqual(result, "2d 1h 3m")