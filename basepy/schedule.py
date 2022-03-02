"""
Python job scheduling for humans.

github.com/dbader/schedule

An in-process scheduler for periodic jobs that uses the builder pattern
for configuration. Schedule lets you run Python functions (or any other
callable) periodically at pre-determined intervals using a simple,
human-friendly syntax.

Inspired by Addam Wiggins' article "Rethinking Cron" [1] and the
"clockwork" Ruby module [2][3].

Features:
    - A simple to use API for scheduling jobs.
    - Very lightweight and no external dependencies.
    - Excellent test coverage.
    - Tested on Python 3.6, 3.7, 3.8, 3.9

Usage:
    >>> import schedule
    >>> import time

    >>> def job(message='stuff'):
    >>>     print("I'm working on:", message)

    >>> schedule.every(10, 'd').do(job)
    >>> schedule.every(1, 'h').do(job, message='things')
    >>> schedule.every(1, 'd').at("10h30m").do(job)
    >>> schedule.every(1, 'd').at("10h30m").until('2022-12-23').do(job)

    >>> while True:
    >>>     schedule.run_pending()
    >>>     time.sleep(1)

[1] https://adam.herokuapp.com/past/2010/4/13/rethinking_cron/
[2] https://github.com/Rykian/clockwork
[3] https://adam.herokuapp.com/past/2010/6/30/replace_cron_with_clockwork/
"""
from collections.abc import Hashable
import datetime
from datetime import timedelta
import functools
import logging
import random
import re
import time
from typing import Set, List, Optional, Callable, Union

logger = logging.getLogger("schedule")


class ScheduleError(Exception):
    """Base schedule exception"""

    pass


class ScheduleValueError(ScheduleError):
    """Base schedule value error"""

    pass


class CancelJob(object):
    """
    Can be returned from a job to unschedule itself.
    """

    pass


class Scheduler(object):
    """
    Objects instantiated by the :class:`Scheduler <Scheduler>` are
    factories to create jobs, keep record of scheduled jobs and
    handle their execution.
    """

    def __init__(self) -> None:
        self.jobs: List[Job] = []

    def run_pending(self) -> None:
        """
        Run all jobs that are scheduled to run.

        Please note that it is *intended behavior that run_pending()
        does not run missed jobs*. For example, if you've registered a job
        that should run every minute and you only call run_pending()
        in one hour increments then your job won't be run 60 times in
        between but only once.
        """
        runnable_jobs = (job for job in self.jobs if job.should_run)
        for job in sorted(runnable_jobs):
            self._run_job(job)

    def run_all(self, delay_seconds: int = 0) -> None:
        """
        Run all jobs regardless if they are scheduled to run or not.

        A delay of `delay` seconds is added between each job. This helps
        distribute system load generated by the jobs more evenly
        over time.

        :param delay_seconds: A delay added between every executed job
        """
        logger.debug(
            "Running *all* %i jobs with %is delay in between",
            len(self.jobs),
            delay_seconds,
        )
        for job in self.jobs[:]:
            self._run_job(job)
            time.sleep(delay_seconds)

    def get_jobs(self, tag: Optional[Hashable] = None) -> List["Job"]:
        """
        Gets scheduled jobs marked with the given tag, or all jobs
        if tag is omitted.

        :param tag: An identifier used to identify a subset of
                    jobs to retrieve
        """
        if tag is None:
            return self.jobs[:]
        else:
            return [job for job in self.jobs if tag in job.tags]

    def clear(self, tag: Optional[Hashable] = None) -> None:
        """
        Deletes scheduled jobs marked with the given tag, or all jobs
        if tag is omitted.

        :param tag: An identifier used to identify a subset of
                    jobs to delete
        """
        if tag is None:
            logger.debug("Deleting *all* jobs")
            del self.jobs[:]
        else:
            logger.debug('Deleting all jobs tagged "%s"', tag)
            self.jobs[:] = (job for job in self.jobs if tag not in job.tags)

    def cancel_job(self, job: "Job") -> None:
        """
        Delete a scheduled job.

        :param job: The job to be unscheduled
        """
        try:
            logger.debug('Cancelling job "%s"', str(job))
            self.jobs.remove(job)
        except ValueError:
            logger.debug('Cancelling not-scheduled job "%s"', str(job))

    def every_s(self, interval: int) -> "Job":
        job = Job(timedelta(seconds=interval), self)
        return job

    def every_delta(self, delta: timedelta) -> "Job":
        job = Job(delta, self)
        return job

    def every(self, number: int, unit="d") -> "Job":
        """
        Schedule a new periodic job.

        :param number: A quantity of a certain time unit
        :parm unit: time unit, can be
            - "w", "week", "weeks"
            - "d", "day", "days"
            - "h", "hour", "hours"
            - "m", "minute", "minutes"
            - "s", "second", "seconds"
        :return: An unconfigured :class:`Job <Job>`
        """
        td = None
        kwargs = {}
        if unit in ['d', 'day', 'days']:
            kwargs['days'] = number
        elif unit in ['h', 'hour', 'hours']:
            kwargs['hours'] = number
        elif unit in ['m', 'minute', 'minutes']:
            kwargs['minutes'] = number
        elif unit in ['s', 'second', 'seconds']:
            kwargs['seconds'] = number
        elif unit in ['w', 'week', 'weeks']:
            kwargs['weeks'] = number
        else:
            raise Exception(f'time unit of {unit} not supported.')

        td = timedelta(**kwargs)
        job = Job(td, self)
        return job

    def _run_job(self, job: "Job") -> None:
        ret = job.run()
        if isinstance(ret, CancelJob) or ret is CancelJob:
            self.cancel_job(job)

    @property
    def next_run(self) -> Optional[datetime.datetime]:
        """
        Datetime when the next job should run.

        :return: A :class:`~datetime.datetime` object
                 or None if no jobs scheduled
        """
        if not self.jobs:
            return None
        return min(self.jobs).next_run

    @property
    def idle_seconds(self) -> Optional[float]:
        """
        :return: Number of seconds until
                 :meth:`next_run <Scheduler.next_run>`
                 or None if no jobs are scheduled
        """
        if not self.next_run:
            return None
        return (self.next_run - datetime.datetime.now()).total_seconds()


class Job(object):
    """
    A periodic job as used by :class:`Scheduler`.

    :param interval: A quantity of a certain time unit
    :param scheduler: The :class:`Scheduler <Scheduler>` instance that
                      this job will register itself with once it has
                      been fully configured in :meth:`Job.do()`.

    Every job runs at a given fixed time interval that is defined by:

    * a :meth:`time unit <Job.second>`
    * a quantity of `time units` defined by `interval`

    A job is usually created and returned by :meth:`Scheduler.every`
    method, which also defines its `interval`.
    """

    def __init__(self, interval: timedelta,  scheduler: Scheduler = None):
        self.period: Optional[timedelta] = interval  # pause interval * unit between runs
        self.job_func: Optional[functools.partial] = None  # the job job_func to run

        self.at_day: Optional[timedelta] = None
        # optional time at which this job runs
        self.at_time: Optional[timedelta] = None


        # datetime of the last run
        self.last_run: Optional[datetime.datetime] = None

        # datetime of the next run
        self.next_run: Optional[datetime.datetime] = None

        # optional time of final run
        self.cancel_after: Optional[datetime.datetime] = None

        self.tags: Set[Hashable] = set()  # unique set of tags for the job
        self.scheduler: Optional[Scheduler] = scheduler  # scheduler to register with

    @property
    def at_offset(self):
        at_day = self.at_day or timedelta(days=0)
        at_time = self.at_time or timedelta(seconds=0)
        return at_day + at_time

    def __lt__(self, other) -> bool:
        """
        PeriodicJobs are sortable based on the scheduled time they
        run next.
        """
        return self.next_run < other.next_run

    def __str__(self) -> str:
        if hasattr(self.job_func, "__name__"):
            job_func_name = self.job_func.__name__  # type: ignore
        else:
            job_func_name = repr(self.job_func)

        return ("Job(period={}, at={}, do={}, args={}, kwargs={})").format(
            self.period,
            self.at_offset,
            job_func_name,
            "()" if self.job_func is None else self.job_func.args,
            "{}" if self.job_func is None else self.job_func.keywords,
        )

    def __repr__(self):
        def format_time(t):
            return t.strftime("%Y-%m-%d %H:%M:%S") if t else "[never]"

        def is_repr(j):
            return not isinstance(j, Job)

        timestats = "(last run: %s, next run: %s)" % (
            format_time(self.last_run),
            format_time(self.next_run),
        )

        if hasattr(self.job_func, "__name__"):
            job_func_name = self.job_func.__name__
        else:
            job_func_name = repr(self.job_func)
        args = [repr(x) if is_repr(x) else str(x) for x in self.job_func.args]
        kwargs = ["%s=%s" % (k, repr(v)) for k, v in self.job_func.keywords.items()]
        call_repr = job_func_name + "(" + ", ".join(args + kwargs) + ")"

        if self.at_time is not None:
            return "Every %s at %s do %s %s" % (
                self.period,
                self.at_time,
                call_repr,
                timestats,
            )
        else:
            fmt = (
                "Every %(interval)s "
                + "do %(call_repr)s %(timestats)s"
            )

            return fmt % dict(
                interval=self.period,
                call_repr=call_repr,
                timestats=timestats,
            )


    def day(self, number:int):
        pass


    def tag(self, *tags: Hashable):
        """
        Tags the job with one or more unique identifiers.

        Tags must be hashable. Duplicate tags are discarded.

        :param tags: A unique list of ``Hashable`` tags.
        :return: The invoked job instance
        """
        if not all(isinstance(tag, Hashable) for tag in tags):
            raise TypeError("Tags must be hashable")
        self.tags.update(tags)
        return self

    def at(self, time_str):

        """
        Specify a particular time that the job should be run at.

        :param time_str: A string in one of the following formats:

            -> `2h3m5s`

        :return: The invoked job instance
        """
        if not isinstance(time_str, str):
            raise TypeError("at() should be passed a string")
        matched = re.match(r"^(\d+h)?(\d+m)?(\d+s)?$", time_str)
        if not matched:
            raise ScheduleValueError(f"time str {time_str} wrong.")

        time_values = map(lambda x: int(x[0:-1]) if x else 0, matched.groups())
        hour: Union[str, int]
        minute: Union[str, int]
        second: Union[str, int]
        hour, minute, second = time_values
        self.at_time = datetime.timedelta(hours=hour, minutes=minute, seconds=second)
        return self

    def at_delta(self, delta:timedelta):
        self.at_time = delta

    def until(
        self,
        until_time: Union[datetime.datetime, timedelta, datetime.time, str],
    ):
        """
        Schedule job to run until the specified moment.

        The job is canceled whenever the next run is calculated and it turns out the
        next run is after the until_time. The job is also canceled right before it runs,
        if the current time is after until_time. This latter case can happen when the
        the job was scheduled to run before until_time, but runs after until_time.

        If until_time is a moment in the past, ScheduleValueError is thrown.

        :param until_time: A moment in the future representing the latest time a job can
           be run. If only a time is supplied, the date is set to today.
           The following formats are accepted:

           - datetime.datetime
           -  timedelta
           - datetime.time
           - String in one of the following formats: "%Y-%m-%d %H:%M:%S",
             "%Y-%m-%d %H:%M", "%Y-%m-%d", "%H:%M:%S", "%H:%M"
             as defined by strptime() behaviour. If an invalid string format is passed,
             ScheduleValueError is thrown.

        :return: The invoked job instance
        """

        if isinstance(until_time, datetime.datetime):
            self.cancel_after = until_time
        elif isinstance(until_time, timedelta):
            self.cancel_after = datetime.datetime.now() + until_time
        elif isinstance(until_time, datetime.time):
            self.cancel_after = datetime.datetime.combine(
                datetime.datetime.now(), until_time
            )
        elif isinstance(until_time, str):
            cancel_after = self._decode_datetimestr(
                until_time,
                [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y-%m-%d",
                    "%H:%M:%S",
                    "%H:%M",
                ],
            )
            if cancel_after is None:
                raise ScheduleValueError("Invalid string format for until()")
            if "-" not in until_time:
                # the until_time is a time-only format. Set the date to today
                now = datetime.datetime.now()
                cancel_after = cancel_after.replace(
                    year=now.year, month=now.month, day=now.day
                )
            self.cancel_after = cancel_after
        else:
            raise TypeError(
                "until() takes a string, datetime.datetime, timedelta, "
                "datetime.time parameter"
            )
        if self.cancel_after < datetime.datetime.now():
            raise ScheduleValueError(
                "Cannot schedule a job to run until a time in the past"
            )
        return self

    def do(self, job_func: Callable, *args, **kwargs):
        """
        Specifies the job_func that should be called every time the
        job runs.

        Any additional arguments are passed on to job_func when
        the job runs.

        :param job_func: The function to be scheduled
        :return: The invoked job instance
        """
        self.job_func = functools.partial(job_func, *args, **kwargs)
        functools.update_wrapper(self.job_func, job_func)
        self._schedule_next_run()
        if self.scheduler is None:
            raise ScheduleError(
                "Unable to a add job to schedule. "
                "Job is not associated with an scheduler"
            )
        self.scheduler.jobs.append(self)
        return self

    @property
    def should_run(self) -> bool:
        """
        :return: ``True`` if the job should be run now.
        """
        assert self.next_run is not None, "must run _schedule_next_run before"
        return datetime.datetime.now() >= self.next_run

    def run(self):
        """
        Run the job and immediately reschedule it.
        If the job's deadline is reached (configured using .until()), the job is not
        run and CancelJob is returned immediately. If the next scheduled run exceeds
        the job's deadline, CancelJob is returned after the execution. In this latter
        case CancelJob takes priority over any other returned value.

        :return: The return value returned by the `job_func`, or CancelJob if the job's
                 deadline is reached.

        """
        if self._is_overdue(datetime.datetime.now()):
            logger.debug("Cancelling job %s", self)
            return CancelJob

        logger.debug("Running job %s", self)
        ret = self.job_func()
        self.last_run = datetime.datetime.now()
        self._schedule_next_run()

        if self._is_overdue(self.next_run):
            logger.debug("Cancelling job %s", self)
            return CancelJob
        return ret

    def _schedule_next_run(self) -> None:
        """
        Compute the instant when this job should run next.
        """
        self.next_run = datetime.datetime.now() + self.period + self.at_offset

    def _is_overdue(self, when: datetime.datetime):
        return self.cancel_after is not None and when > self.cancel_after

    def _decode_datetimestr(
        self, datetime_str: str, formats: List[str]
    ) -> Optional[datetime.datetime]:
        for f in formats:
            try:
                return datetime.datetime.strptime(datetime_str, f)
            except ValueError:
                pass
        return None


#: Default :class:`Scheduler <Scheduler>` object
scheduler = Scheduler()
