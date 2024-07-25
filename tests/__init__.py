import datetime
import io
import os.path
import pkgutil

from twisted.logger import eventAsText

from scrapyd.launcher import ScrapyProcessProtocol


def touch(path):
    path.parent.mkdir(parents=True)
    path.touch()


def get_egg_data(basename):
    return pkgutil.get_data("tests", f"fixtures/{basename}.egg")


def has_settings():
    return os.path.exists("scrapy.cfg")


def root_add_version(root, project, version, basename):
    root.eggstorage.put(io.BytesIO(get_egg_data(basename)), project, version)


def get_message(captured):
    return eventAsText(captured[0]).split(" ", 1)[1]


def get_finished_job(project="p1", spider="s1", job="j1", start_time=None, end_time=None):
    if start_time is None:
        start_time = datetime.datetime.now()
    if end_time is None:
        end_time = datetime.datetime.now()
    process = ScrapyProcessProtocol(project, spider, job, env={}, args=[])
    process.start_time = start_time
    process.end_time = end_time
    return process
