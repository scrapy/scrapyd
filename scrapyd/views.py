from twisted.web.template import Element, renderer, XMLFile, tags,flattenString
from twisted.python.filepath import FilePath
from os import path
from datetime import datetime,timedelta
from zope.interface import implementer
from scrapy.utils.misc import load_object
from six.moves.urllib.parse import urlparse


def microsec_trunc(timelike):
    if hasattr(timelike, 'microsecond'):
        ms = timelike.microsecond
    else:
        ms = timelike.microseconds
    return timelike - timedelta(microseconds=ms)


def load_template(file):
    scrapyd_views = path.join(path.dirname(path.abspath(__file__)),"templates")
    _path = path.join(scrapyd_views,file)
    return XMLFile(FilePath(_path))

class BaseElement(Element):
    @property
    def loader(self):
        return load_template(self._template_file_)
    @renderer
    def footer(self,request,tag):
        return load_template("footer.html").load()

    @renderer
    def header(self,request,tag):
        return load_template("header.html").load()


class HomeElement(BaseElement):
    _template_file_  = "home.html"

    @renderer
    def projects(self,request,tag):
        return tag(", ".join(self._root.scheduler.list_projects()))

    @renderer
    def local_items(self,request,tag):
        itemsdir = self._root.config.get('items_dir')
        local_items = itemsdir and (urlparse(itemsdir).scheme.lower() in ['', 'file'])
        if local_items:
            return tags.li(tags.a("Items",href="/items"))

        return ""

class JobsElement(BaseElement):
    _template_file_  = "jobs.html"
    def createJob(self,**job):
        return dict(
            project = str(job['project']) if 'project' in job else '',
            spider = str(job['spider']) if 'spider' in job else '',
            job = str(job['job']) if 'job' in job else '',
            pid = str(job['pid']) if 'pid' in job else '',
            start = str(microsec_trunc(job['start'])) if 'start' in job else '',
            runtime = str(microsec_trunc(job['runtime'])) if 'runtime' in job else '',
            finish = str(microsec_trunc(job['finish'])) if 'finish' in job else '',
            log = str(job['log']) if 'log' in job else '',
            items = str(job['items']) if 'items' in job else '',
        )
    @renderer
    def pending(self,request,tag):
        data = [self.createJob(
                project=project or "", spider=m['name'], job=m['_job'],
            )
            for project, queue in self._root.poller.queues.items()
            for m in queue.list()
        ]
        for job in data:
            yield tag.clone().fillSlots(**job)
        return ""

    @renderer
    def finished(self,request,tag):
        data= [self.createJob(
                project=p.project, spider=p.spider,job=p.job,
                start=p.start_time,
                runtime=p.end_time - p.start_time,
                finish=p.end_time,
                log='/logs/%s/%s/%s.log' % (p.project, p.spider, p.job),
                items='/items/%s/%s/%s.jl' % (p.project, p.spider, p.job),
            )
            for p in self._root.launcher.finished
        ]
        for job in data:
            yield tag.clone().fillSlots(**job)
        return ""

    @renderer
    def running(self,request,tag):
        data = [
            self.createJob(
                project=p.project, spider=p.spider,
                job=p.job, pid=p.pid,
                start=p.start_time,
                runtime=datetime.now() - p.start_time,
                log='/logs/%s/%s/%s.log' % (p.project, p.spider, p.job),
                items='/items/%s/%s/%s.jl' % (p.project, p.spider, p.job),
            )
            for p in self._root.launcher.processes.values()
        ]
        for job in data:
            yield tag.clone().fillSlots(**job)
        return ""
