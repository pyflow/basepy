"""Unit tests for schedule.py"""
import datetime
import functools
import mock


from  basepy.schedule import (
    scheduler,
    ScheduleError,
    ScheduleValueError,
)


def make_mock_job(name=None):
    job = mock.Mock()
    job.__name__ = name or "job"
    return job


class mock_datetime(object):
    """
    Monkey-patch datetime for predictable results
    """

    def __init__(self, year, month, day, hour, minute, second=0):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second

    def __enter__(self):
        class MockDate(datetime.datetime):
            @classmethod
            def today(cls):
                return cls(self.year, self.month, self.day)

            @classmethod
            def now(cls):
                return cls(
                    self.year,
                    self.month,
                    self.day,
                    self.hour,
                    self.minute,
                    self.second,
                )

        self.original_datetime = datetime.datetime
        datetime.datetime = MockDate

        return MockDate(
            self.year, self.month, self.day, self.hour, self.minute, self.second
        )

    def __exit__(self, *args, **kwargs):
        datetime.datetime = self.original_datetime





def test_at_time():
    mock_job = make_mock_job()
    with mock_datetime(2022, 3, 2, 20, 32):
        assert scheduler.every(1, 'd').do(mock_job).next_run.hour == 20
