import socket
from datetime import datetime, timedelta
from html import escape
from urllib.parse import quote, urlparse

from scrapy.utils.misc import load_object
from twisted.application.service import IServiceCollection
from twisted.python import filepath
from twisted.web import resource, static

from scrapyd.interfaces import IEggStorage, IPoller, ISpiderScheduler
from scrapyd.jobstorage import job_items_url, job_log_url


class PrefixHeaderMixin:
    def get_base_path(self, txrequest):
        return txrequest.getHeader(self.prefix_header) or ''


# Use local DirectoryLister class.
class File(static.File):
    def directoryListing(self):
        path = self.path
        names = self.listNames()
        return DirectoryLister(
            path, names, self.contentTypes, self.contentEncodings, self.defaultType
        )


# Add "Last modified" column.
class DirectoryLister(static.DirectoryLister):
    template = """<html>
<head>
<title>%(header)s</title>
<style>
.even-dir { background-color: #efe0ef }
.even { background-color: #eee }
.odd-dir {background-color: #f0d0ef }
.odd { background-color: #dedede }
.icon { text-align: center }
.listing {
    margin-left: auto;
    margin-right: auto;
    width: 50%%;
    padding: 0.1em;
    }

body { border: 0; padding: 0; margin: 0; background-color: #efefef; }
h1 {padding: 0.1em; background-color: #777; color: white; border-bottom: thin white dashed;}

</style>
</head>

<body>
<h1>%(header)s</h1>

<table>
    <thead>
        <tr>
            <th>Filename</th>
            <th>Size</th>
            <th>Last modified</th>
            <th>Content type</th>
            <th>Content encoding</th>
        </tr>
    </thead>
    <tbody>
%(tableContent)s
    </tbody>
</table>

</body>
</html>
"""

    linePattern = """<tr class="%(class)s">
    <td><a href="%(href)s">%(text)s</a></td>
    <td>%(size)s</td>
    <td>%(modified)s</td>
    <td>%(type)s</td>
    <td>%(encoding)s</td>
</tr>
"""

    def _getFilesAndDirectories(self, directory):
        files = []
        dirs = []

        for path in directory:
            if isinstance(path, bytes):
                path = path.decode("utf8")

            url = quote(path, "/")
            escapedPath = escape(path)
            childPath = filepath.FilePath(self.path).child(path)
            modified = datetime.fromtimestamp(childPath.getModificationTime()).strftime("%Y-%m-%d %H:%M")  # NEW

            if childPath.isdir():
                dirs.append(
                    {
                        "text": escapedPath + "/",
                        "href": url + "/",
                        "size": "",
                        "type": "[Directory]",
                        "encoding": "",
                        "modified": modified,  # NEW
                    }
                )
            else:
                mimetype, encoding = static.getTypeAndEncoding(
                    path, self.contentTypes, self.contentEncodings, self.defaultType
                )
                try:
                    size = childPath.getsize()
                except OSError:
                    continue
                files.append(
                    {
                        "text": escapedPath,
                        "href": url,
                        "type": "[%s]" % mimetype,
                        "encoding": (encoding and "[%s]" % encoding or ""),
                        "size": static.formatFileSize(size),
                        "modified": modified,  # NEW
                    }
                )
        return dirs, files


class Root(resource.Resource):

    def __init__(self, config, app):
        resource.Resource.__init__(self)
        self.debug = config.getboolean('debug', False)
        self.runner = config.get('runner')
        self.prefix_header = config.get('prefix_header')
        logsdir = config.get('logs_dir')
        itemsdir = config.get('items_dir')
        self.local_items = itemsdir and (urlparse(itemsdir).scheme.lower() in ['', 'file'])
        self.app = app
        self.nodename = config.get('node_name', socket.gethostname())
        self.putChild(b'', Home(self, self.local_items))
        if logsdir:
            self.putChild(b'logs', File(logsdir.encode('ascii', 'ignore'), 'text/plain'))
        if self.local_items:
            self.putChild(b'items', File(itemsdir, 'text/plain'))
        self.putChild(b'jobs', Jobs(self, self.local_items))
        services = config.items('services', ())
        for servName, servClsName in services:
            servCls = load_object(servClsName)
            self.putChild(servName.encode('utf-8'), servCls(self))
        self.update_projects()

    def update_projects(self):
        self.poller.update_projects()
        self.scheduler.update_projects()

    @property
    def launcher(self):
        app = IServiceCollection(self.app, self.app)
        return app.getServiceNamed('launcher')

    @property
    def scheduler(self):
        return self.app.getComponent(ISpiderScheduler)

    @property
    def eggstorage(self):
        return self.app.getComponent(IEggStorage)

    @property
    def poller(self):
        return self.app.getComponent(IPoller)


class Home(PrefixHeaderMixin, resource.Resource):

    def __init__(self, root, local_items):
        resource.Resource.__init__(self)
        self.root = root
        self.local_items = local_items
        self.prefix_header = root.prefix_header

    def render_GET(self, txrequest):
        vars = {
            'base_path': self.get_base_path(txrequest),
        }
        s = """\
<html>
<head><title>Scrapyd</title></head>
<body>
<h1>Scrapyd</h1>
<ul>
<li><a href="%(base_path)s/jobs">Jobs</a></li>
"""
        if self.local_items:
            s += '<li><a href="%(base_path)s/items/">Items</a></li>\n'
        s += """\
<li><a href="%(base_path)s/logs/">Logs</a></li>
<li><a href="https://scrapyd.readthedocs.io/en/latest/">Documentation</a></li>
</ul>
""" % vars
        if self.root.scheduler.list_projects():
            s += '<p>Available projects:<p>\n<ul>\n'
            for project_name in sorted(self.root.scheduler.list_projects()):
                s += f'<li>{project_name}</li>\n'
            s += '</ul>\n'
        else:
            s += '<p>No projects available.</p>\n'
        s += """
<h2>How to schedule a spider?</h2>

<p>To schedule a spider you need to use the API (this web UI is only for
monitoring)</p>

<p>Example using <a href="https://curl.se/">curl</a>:</p>
<p><code>curl http://localhost:6800/schedule.json -d project=default -d spider=somespider</code></p>

<p>For more information about the API, see the
<a href="https://scrapyd.readthedocs.io/en/latest/">Scrapyd documentation</a></p>
</body>
</html>
"""
        txrequest.setHeader('Content-Type', 'text/html; charset=utf-8')
        s = (s % vars).encode('utf8')
        txrequest.setHeader('Content-Length', str(len(s)))
        return s


def microsec_trunc(timelike):
    if hasattr(timelike, 'microsecond'):
        ms = timelike.microsecond
    else:
        ms = timelike.microseconds
    return timelike - timedelta(microseconds=ms)


class Jobs(PrefixHeaderMixin, resource.Resource):

    def __init__(self, root, local_items):
        resource.Resource.__init__(self)
        self.root = root
        self.local_items = local_items
        self.prefix_header = root.prefix_header

    cancel_button = """
    <form method="post" onsubmit="return confirm('Are you sure?');" action="{base_path}/cancel.json">
    <input type="hidden" name="project" value="{project}"/>
    <input type="hidden" name="job" value="{jobid}"/>
    <input type="submit" style="float: left;" value="Cancel"/>
    </form>
    """.format

    header_cols = [
        'Project', 'Spider',
        'Job', 'PID',
        'Start', 'Runtime', 'Finish',
        'Log', 'Items',
        'Cancel',
    ]

    def gen_css(self):
        css = [
            '#jobs>thead td {text-align: center; font-weight: bold}',
            '#jobs>tbody>tr:first-child {background-color: #eee}',
        ]
        if not self.local_items:
            col_idx = self.header_cols.index('Items') + 1
            css.append('#jobs>*>tr>*:nth-child(%d) {display: none}' % col_idx)
        if b'cancel.json' not in self.root.children:
            col_idx = self.header_cols.index('Cancel') + 1
            css.append('#jobs>*>tr>*:nth-child(%d) {display: none}' % col_idx)
        return '\n'.join(css)

    def prep_row(self, cells):
        if not isinstance(cells, dict):
            assert len(cells) == len(self.header_cols)
        else:
            cells = [cells.get(k) for k in self.header_cols]
        cells = ['<td>%s</td>' % ('' if c is None else c) for c in cells]
        return '<tr>%s</tr>' % ''.join(cells)

    def prep_doc(self):
        return (
            '<html>'
            '<head>'
            '<title>Scrapyd</title>'
            '<style type="text/css">' + self.gen_css() + '</style>'
            '</head>'
            '<body><h1>Jobs</h1>'
            '<p><a href="./">Go up</a></p>'
            + self.prep_table() +
            '</body>'
            '</html>'
        )

    def prep_table(self):
        return (
            '<table id="jobs" border="1">'
            '<thead>' + self.prep_row(self.header_cols) + '</thead>'
            '<tbody>'
            + '<tr><th colspan="%d">Pending</th></tr>' % len(self.header_cols)
            + self.prep_tab_pending() +
            '</tbody>'
            '<tbody>'
            + '<tr><th colspan="%d">Running</th></tr>' % len(self.header_cols)
            + self.prep_tab_running() +
            '</tbody>'
            '<tbody>'
            + '<tr><th colspan="%d">Finished</th></tr>' % len(self.header_cols)
            + self.prep_tab_finished() +
            '</tbody>'
            '</table>'
        )

    def prep_tab_pending(self):
        return '\n'.join(
            self.prep_row({
                "Project": project,
                "Spider": m['name'],
                "Job": m['_job'],
                "Cancel": self.cancel_button(project=project, jobid=m['_job'], base_path=self.base_path),
            })
            for project, queue in self.root.poller.queues.items()
            for m in queue.list()
        )

    def prep_tab_running(self):
        return '\n'.join(
            self.prep_row({
                "Project": p.project,
                "Spider": p.spider,
                "Job": p.job,
                "PID": p.pid,
                "Start": microsec_trunc(p.start_time),
                "Runtime": microsec_trunc(datetime.now() - p.start_time),
                "Log": f'<a href="{self.base_path}{job_log_url(p)}">Log</a>',
                "Items": f'<a href="{self.base_path}{job_items_url(p)}">Items</a>',
                "Cancel": self.cancel_button(project=p.project, jobid=p.job, base_path=self.base_path),
            })
            for p in self.root.launcher.processes.values()
        )

    def prep_tab_finished(self):
        return '\n'.join(
            self.prep_row({
                "Project": p.project,
                "Spider": p.spider,
                "Job": p.job,
                "Start": microsec_trunc(p.start_time),
                "Runtime": microsec_trunc(p.end_time - p.start_time),
                "Finish": microsec_trunc(p.end_time),
                "Log": f'<a href="{self.base_path}{job_log_url(p)}">Log</a>',
                "Items": f'<a href="{self.base_path}{job_items_url(p)}">Items</a>',
            })
            for p in self.root.launcher.finished
        )

    def render(self, txrequest):
        self.base_path = self.get_base_path(txrequest)
        doc = self.prep_doc()
        txrequest.setHeader('Content-Type', 'text/html; charset=utf-8')
        doc = doc.encode('utf-8')
        txrequest.setHeader('Content-Length', str(len(doc)))
        return doc
