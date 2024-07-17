from datetime import datetime

from zope.interface import implementer

from scrapyd.interfaces import IJobStorage
from scrapyd.sqlite import SqliteFinishedJobs
from scrapyd.utils import sqlite_connection_string


def job_log_url(job):
    return f"/logs/{job.project}/{job.spider}/{job.job}.log"


def job_items_url(job):
    return f"/items/{job.project}/{job.spider}/{job.job}.jl"


class Job(object):
    def __init__(self, project, spider, job=None, start_time=None, end_time=None):
        self.project = project
        self.spider = spider
        self.job = job
        self.start_time = start_time if start_time else datetime.now()
        self.end_time = end_time if end_time else datetime.now()


@implementer(IJobStorage)
class MemoryJobStorage(object):

    def __init__(self, config):
        self.jobs = []
        self.finished_to_keep = config.getint('finished_to_keep', 100)

    def add(self, job):
        self.jobs.append(job)
        del self.jobs[:-self.finished_to_keep]  # keep last x finished jobs

    def list(self):
        return self.jobs

    def __len__(self):
        return len(self.jobs)

    def __iter__(self):
        for j in self.jobs:
            yield j


@implementer(IJobStorage)
class SqliteJobStorage(object):

    def __init__(self, config):
        self.jstorage = SqliteFinishedJobs(sqlite_connection_string(config, 'jobs'), "finished_jobs")
        self.finished_to_keep = config.getint('finished_to_keep', 100)

    def add(self, job):
        self.jstorage.add(job)
        self.jstorage.clear(self.finished_to_keep)

    def list(self):
        return list(self.__iter__())

    def __len__(self):
        return len(self.jstorage)

    def __iter__(self):
        for j in self.jstorage:
            yield Job(project=j[0], spider=j[1], job=j[2],
                      start_time=j[3], end_time=j[4])
