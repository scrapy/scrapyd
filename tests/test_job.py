import datetime

from scrapyd.jobstorage import Job


def test_job_repr():
    job = Job(
        "p1",
        "s1",
        start_time=datetime.datetime(2001, 2, 3, 4, 5, 6, 0),
        end_time=datetime.datetime(2001, 2, 3, 4, 5, 7, 0),
    )
    assert (
        repr(job)
        == "Job(project=p1, spider=s1, job=None, start_time=2001-02-03 04:05:06, end_time=2001-02-03 04:05:07)"
    )
