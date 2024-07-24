"""
.. versionadded:: 1.3.0
   Job storage was previously in-memory only and managed by the launcher.
"""

import datetime

from zope.interface import implementer

from scrapyd import sqlite
from scrapyd.interfaces import IJobStorage


class Job:
    def __init__(self, project, spider, job=None, start_time=None, end_time=None):
        self.project = project
        self.spider = spider
        self.job = job
        self.start_time = start_time if start_time else datetime.datetime.now()
        self.end_time = end_time if end_time else datetime.datetime.now()

    # For equality assertions in tests.
    def __eq__(self, other):
        return (
            self.project == other.project
            and self.spider == other.spider
            and self.job == other.job
            and self.start_time == other.start_time
            and self.end_time == other.end_time
        )

    # For error messsages in tests.
    def __repr__(self):
        return (
            f"Job(project={self.project}, spider={self.spider}, job={self.job}, "
            f"start_time={self.start_time}, end_time={self.end_time})"
        )


@implementer(IJobStorage)
class MemoryJobStorage:
    def __init__(self, config):
        self.jobs = []
        self.finished_to_keep = config.getint("finished_to_keep", 100)

    def add(self, job):
        self.jobs.append(job)
        del self.jobs[: -self.finished_to_keep]  # keep last x finished jobs

    def list(self):
        return list(self)

    def __len__(self):
        return len(self.jobs)

    def __iter__(self):
        yield from reversed(self.jobs)


@implementer(IJobStorage)
class SqliteJobStorage:
    def __init__(self, config):
        self.jobs = sqlite.initialize(sqlite.SqliteFinishedJobs, config, "jobs", "finished_jobs")
        self.finished_to_keep = config.getint("finished_to_keep", 100)

    def add(self, job):
        self.jobs.add(job)
        self.jobs.clear(self.finished_to_keep)

    def list(self):
        return list(self)

    def __len__(self):
        return len(self.jobs)

    def __iter__(self):
        for project, spider, job, start_time, end_time in self.jobs:
            yield Job(project=project, spider=spider, job=job, start_time=start_time, end_time=end_time)
