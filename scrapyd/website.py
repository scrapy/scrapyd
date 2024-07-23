import socket
from datetime import datetime, timedelta
from html import escape
from urllib.parse import quote, urlparse

from scrapy.utils.misc import load_object
from twisted.application.service import IServiceCollection
from twisted.python import filepath
from twisted.web import resource, static

from scrapyd.interfaces import IEggStorage, IPoller, ISpiderScheduler
from scrapyd.utils import job_items_url, job_log_url


class PrefixHeaderMixin:
    def get_base_path(self, txrequest):
        return txrequest.getHeader(self.prefix_header) or ""


# Use local DirectoryLister class.
class File(static.File):
    def directoryListing(self):
        path = self.path
        names = self.listNames()
        return DirectoryLister(path, names, self.contentTypes, self.contentEncodings, self.defaultType)


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
                path = path.decode()  # noqa: PLW2901 from Twisted

            url = quote(path, "/")
            escaped_path = escape(path)
            child_path = filepath.FilePath(self.path).child(path)
            modified = datetime.fromtimestamp(child_path.getModificationTime()).strftime("%Y-%m-%d %H:%M")  # NEW

            if child_path.isdir():
                dirs.append(
                    {
                        "text": escaped_path + "/",
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
                    size = child_path.getsize()
                except OSError:
                    continue
                files.append(
                    {
                        "text": escaped_path,
                        "href": url,
                        "type": f"[{mimetype}]",
                        "encoding": (encoding and f"[{encoding}]" or ""),
                        "size": static.formatFileSize(size),
                        "modified": modified,  # NEW
                    }
                )
        return dirs, files


class Root(resource.Resource):
    def __init__(self, config, app):
        resource.Resource.__init__(self)

        logs_dir = config.get("logs_dir")
        items_dir = config.get("items_dir")

        self.app = app
        self.debug = config.getboolean("debug", False)
        self.runner = config.get("runner", "scrapyd.runner")
        self.prefix_header = config.get("prefix_header")
        self.local_items = items_dir and (urlparse(items_dir).scheme.lower() in ["", "file"])
        self.nodename = config.get("node_name", socket.gethostname())

        self.putChild(b"", Home(self, self.local_items))
        if logs_dir:
            self.putChild(b"logs", File(logs_dir, "text/plain"))
        if self.local_items:
            self.putChild(b"items", File(items_dir, "text/plain"))
        self.putChild(b"jobs", Jobs(self, self.local_items))
        for service_name, service_path in config.items("services", default=[]):
            service_cls = load_object(service_path)
            self.putChild(service_name.encode(), service_cls(self))

    def update_projects(self):
        self.poller.update_projects()
        self.scheduler.update_projects()

    @property
    def launcher(self):
        app = IServiceCollection(self.app, self.app)
        return app.getServiceNamed("launcher")

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
        base_path = self.get_base_path(txrequest)

        s = f"""\
<html>
<head><title>Scrapyd</title></head>
<body>
<h1>Scrapyd</h1>
<ul>
<li><a href="{base_path}/jobs">Jobs</a></li>
"""
        if self.local_items:
            s += f'<li><a href="{base_path}/items/">Items</a></li>\n'
        s += f"""\
<li><a href="{base_path}/logs/">Logs</a></li>
<li><a href="https://scrapyd.readthedocs.io/en/latest/">Documentation</a></li>
</ul>
"""
        if projects := self.root.scheduler.list_projects():
            s += "<p>Available projects:<p>\n<ul>\n"
            for project_name in sorted(projects):
                s += f"<li>{escape(project_name)}</li>\n"
            s += "</ul>\n"
        else:
            s += "<p>No projects available.</p>\n"
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
        txrequest.setHeader("Content-Type", "text/html; charset=utf-8")
        s = s.encode()
        txrequest.setHeader("Content-Length", str(len(s)))
        return s


def microsec_trunc(timelike):
    # microsecond for datetime, microseconds for timedelta.
    ms = timelike.microsecond if hasattr(timelike, "microsecond") else timelike.microseconds
    return timelike - timedelta(microseconds=ms)


def cancel_button(project, jobid, base_path):
    return f"""
    <form method="post" onsubmit="return confirm('Are you sure?');" action="{base_path}/cancel.json">
    <input type="hidden" name="project" value="{escape(project)}"/>
    <input type="hidden" name="job" value="{escape(jobid)}"/>
    <input type="submit" style="float: left;" value="Cancel"/>
    </form>
    """


class Jobs(PrefixHeaderMixin, resource.Resource):
    def __init__(self, root, local_items):
        resource.Resource.__init__(self)
        self.root = root
        self.local_items = local_items
        self.prefix_header = root.prefix_header

    header_cols = (
        "Project",
        "Spider",
        "Job",
        "PID",
        "Start",
        "Runtime",
        "Finish",
        "Log",
        "Items",
        "Cancel",
    )

    def gen_css(self):
        css = [
            "#jobs>thead td {text-align: center; font-weight: bold}",
            "#jobs>tbody>tr:first-child {background-color: #eee}",
        ]
        if not self.local_items:
            col_idx = self.header_cols.index("Items") + 1
            css.append(f"#jobs>*>tr>*:nth-child({col_idx}) {{display: none}}")
        if b"cancel.json" not in self.root.children:
            col_idx = self.header_cols.index("Cancel") + 1
            css.append(f"#jobs>*>tr>*:nth-child({col_idx}) {{display: none}}")
        return "\n".join(css)

    def prep_row(self, cells):
        if isinstance(cells, dict):
            cells = [cells.get(key) for key in self.header_cols]
        cells = [f"<td>{'' if cell is None else cell}</td>" for cell in cells]
        return f"<tr>{''.join(cells)}</tr>"

    def prep_doc(self):
        return (
            "<html>"
            "<head>"
            "<title>Scrapyd</title>"
            '<style type="text/css">' + self.gen_css() + "</style>"
            "</head>"
            "<body><h1>Jobs</h1>"
            '<p><a href="./">Go up</a></p>' + self.prep_table() + "</body>"
            "</html>"
        )

    def prep_table(self):
        return (
            '<table id="jobs" border="1">'
            "<thead>" + self.prep_row(self.header_cols) + "</thead>"
            "<tbody>"
            + f'<tr><th colspan="{len(self.header_cols)}">Pending</th></tr>'
            + self.prep_tab_pending()
            + "</tbody>"
            "<tbody>"
            + f'<tr><th colspan="{len(self.header_cols)}">Running</th></tr>'
            + self.prep_tab_running()
            + "</tbody>"
            "<tbody>"
            + f'<tr><th colspan="{len(self.header_cols)}">Finished</th></tr>'
            + self.prep_tab_finished()
            + "</tbody>"
            "</table>"
        )

    def prep_tab_pending(self):
        return "\n".join(
            self.prep_row(
                {
                    "Project": escape(project),
                    "Spider": escape(message["name"]),
                    "Job": escape(message["_job"]),
                    "Cancel": cancel_button(project=project, jobid=message["_job"], base_path=self.base_path),
                }
            )
            for project, queue in self.root.scheduler.queues.items()
            for message in queue.list()
        )

    def prep_tab_running(self):
        return "\n".join(
            self.prep_row(
                {
                    "Project": escape(process.project),
                    "Spider": escape(process.spider),
                    "Job": escape(process.job),
                    "PID": process.pid,
                    "Start": microsec_trunc(process.start_time),
                    "Runtime": microsec_trunc(datetime.now() - process.start_time),
                    "Log": f'<a href="{self.base_path}{job_log_url(process)}">Log</a>',
                    "Items": f'<a href="{self.base_path}{job_items_url(process)}">Items</a>',
                    "Cancel": cancel_button(project=process.project, jobid=process.job, base_path=self.base_path),
                }
            )
            for process in self.root.launcher.processes.values()
        )

    def prep_tab_finished(self):
        return "\n".join(
            self.prep_row(
                {
                    "Project": escape(job.project),
                    "Spider": escape(job.spider),
                    "Job": escape(job.job),
                    "Start": microsec_trunc(job.start_time),
                    "Runtime": microsec_trunc(job.end_time - job.start_time),
                    "Finish": microsec_trunc(job.end_time),
                    "Log": f'<a href="{self.base_path}{job_log_url(job)}">Log</a>',
                    "Items": f'<a href="{self.base_path}{job_items_url(job)}">Items</a>',
                }
            )
            for job in self.root.launcher.finished
        )

    def render(self, txrequest):
        self.base_path = self.get_base_path(txrequest)
        doc = self.prep_doc()
        txrequest.setHeader("Content-Type", "text/html; charset=utf-8")
        doc = doc.encode()
        txrequest.setHeader("Content-Length", str(len(doc)))
        return doc
