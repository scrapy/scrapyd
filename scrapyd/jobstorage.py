"""
.. versionadded:: 1.3.0
   Job storage was previously in-memory only and managed by the launcher.
"""

from zope.interface import implementer

from scrapyd import sqlite
from scrapyd.interfaces import IJobStorage
from scrapyd.launcher import ScrapyProcessProtocol


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
        for project, spider, jobid, start_time, end_time in self.jobs:
            job = ScrapyProcessProtocol(project, spider, jobid, env={}, args=[])
            job.start_time = start_time
            job.end_time = end_time
            yield job
