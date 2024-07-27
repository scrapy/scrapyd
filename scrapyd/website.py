import os.path
import socket
from datetime import datetime, timedelta
from html import escape
from textwrap import dedent, indent
from urllib.parse import quote, urlsplit

from scrapy.utils.misc import load_object
from twisted.application.service import IServiceCollection
from twisted.python import filepath
from twisted.web import resource, static

from scrapyd.interfaces import IEggStorage, IPoller, ISpiderScheduler
from scrapyd.utils import local_items


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


def _get_file_url(base, directory, job, extension):
    if os.path.exists(os.path.join(directory, job.project, job.spider, f"{job.job}.{extension}")):
        return f"/{base}/{job.project}/{job.spider}/{job.job}.{extension}"
    return None


class Root(resource.Resource):
    def __init__(self, config, app):
        super().__init__()

        self.app = app
        self.logs_dir = config.get("logs_dir", "logs")
        self.items_dir = config.get("items_dir", "")
        self.debug = config.getboolean("debug", False)
        self.runner = config.get("runner", "scrapyd.runner")
        self.prefix_header = config.get("prefix_header", "x-forwarded-prefix")
        self.local_items = local_items(self.items_dir, urlsplit(self.items_dir))
        self.node_name = config.get("node_name", socket.gethostname())

        if self.logs_dir:
            self.putChild(b"logs", File(self.logs_dir, "text/plain"))
        if self.local_items:
            self.putChild(b"items", File(self.items_dir, "text/plain"))

        for service_name, service_path in config.items("services", default=[]):
            if service_path:
                service_cls = load_object(service_path)
                self.putChild(service_name.encode(), service_cls(self))

        # Add web UI last, since its behavior can depend on others' presence.
        self.putChild(b"", Home(self))
        self.putChild(b"jobs", Jobs(self))

    def update_projects(self):
        self.poller.update_projects()
        self.scheduler.update_projects()

    def get_log_url(self, job):
        return _get_file_url("logs", self.logs_dir, job, "log")

    def get_item_url(self, job):
        if self.local_items:
            return _get_file_url("items", self.items_dir, job, "jl")
        return None

    @property
    def launcher(self):
        return IServiceCollection(self.app, self.app).getServiceNamed("launcher")

    @property
    def scheduler(self):
        return self.app.getComponent(ISpiderScheduler)

    @property
    def eggstorage(self):
        return self.app.getComponent(IEggStorage)

    @property
    def poller(self):
        return self.app.getComponent(IPoller)


class PrefixHeaderMixin:
    def get_base_path(self, txrequest):
        return txrequest.getHeader(self.root.prefix_header) or ""


class Home(PrefixHeaderMixin, resource.Resource):
    def __init__(self, root):
        super().__init__()
        self.root = root

    def prepare_projects(self):
        if projects := self.root.scheduler.list_projects():
            lis = "\n".join(f"<li>{escape(project_name)}</li>" for project_name in sorted(projects))
            return f"<p>Scrapy projects:</p>\n<ul>\n{indent(lis, '    ')}\n</ul>"
        return "<p>No Scrapy projects yet.</p>"

    def render_GET(self, txrequest):
        base_path = self.get_base_path(txrequest)

        content = dedent(
            f"""\
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Scrapyd</title>
                <style>
                    body {{ font-family: system-ui, sans-serif; }}
                </style>
            </head>
            <body>
                <h1>Scrapyd</h1>

                <ul>
                    <li><a href="{base_path}/jobs">Jobs</a></li>
                    {f'<li><a href="{base_path}/items/">Items</a></li>' if self.root.local_items else ''}
                    <li><a href="{base_path}/logs/">Logs</a></li>
                    <li><a href="https://scrapyd.readthedocs.io/en/latest/">Documentation</a></li>
                </ul>

{indent(self.prepare_projects(), "                ")}

                <p>
                    This web UI is for monitoring only. To upload projects and schedule crawls, use the API.
                    For example, using <a href="https://curl.se/">curl</a>:
                </p>

                <p>
                    <code>curl http://localhost:6800/schedule.json -d project=default -d spider=somespider</code>
                </p>

                <p>
                    See the <a href="https://scrapyd.readthedocs.io/en/latest/">Scrapyd documentation</a> for details.
                </p>
            </body>
            </html>
            """
        )
        content = content.encode()

        txrequest.setHeader("Content-Type", "text/html; charset=utf-8")
        txrequest.setHeader("Content-Length", str(len(content)))
        return content


def no_microseconds(timelike):
    # microsecond for datetime, microseconds for timedelta.
    ms = timelike.microsecond if hasattr(timelike, "microsecond") else timelike.microseconds
    return timelike - timedelta(microseconds=ms)


class Jobs(PrefixHeaderMixin, resource.Resource):
    def __init__(self, root):
        super().__init__()
        self.root = root

        self.headers = [
            "Project",
            "Spider",
            "Job",
            "PID",
            "Start",
            "Runtime",
            "Finish",
            "Log",
        ]
        # Hide the Items column if items_dir isn't local.
        if self.root.local_items:
            self.headers.append("Items")
        # Hide the Cancel column if no cancel.json webservice.
        if b"cancel.json" in self.root.children:
            self.headers.append("Cancel")

    def cancel_button(self, project, job):
        return dedent(
            f"""
            <form method="post" onsubmit="return confirm('Are you sure?');" action="{self.base_path}/cancel.json">
            <input type="hidden" name="project" value="{escape(project)}">
            <input type="hidden" name="job" value="{escape(job)}">
            <input type="submit" style="float: left;" value="Cancel">
            </form>
            """
        )

    def html_log_url(self, job):
        if url := self.root.get_log_url(job):
            return f'<a href="{self.base_path}{url}">Log</a>'
        return None

    def html_item_url(self, job):
        if url := self.root.get_item_url(job):
            return f'<a href="{self.base_path}{url}">Items</a>'
        return None

    def prepare_headers(self):
        ths = "\n".join(f"<th>{header}</th>" for header in self.headers)
        return f"<tr>\n{indent(ths, '    ')}\n</tr>"

    def prepare_row(self, row):
        tds = "\n".join(f"<td>{'' if row.get(header) is None else row[header]}</td>" for header in self.headers)
        return f"<tr>\n{indent(tds, '    ')}\n</tr>"

    def prepare_pending(self):
        return "\n".join(
            self.prepare_row(
                {
                    "Project": escape(project),
                    "Spider": escape(message["name"]),
                    "Job": escape(message["_job"]),
                    "Cancel": self.cancel_button(project, message["_job"]),
                }
            )
            for project, queue in self.root.poller.queues.items()
            for message in queue.list()
        )

    def prepare_running(self):
        return "\n".join(
            self.prepare_row(
                {
                    "Project": escape(process.project),
                    "Spider": escape(process.spider),
                    "Job": escape(process.job),
                    "PID": process.pid,
                    "Start": no_microseconds(process.start_time),
                    "Runtime": no_microseconds(datetime.now() - process.start_time),
                    "Log": self.html_log_url(process),
                    "Items": self.html_item_url(process),
                    "Cancel": self.cancel_button(process.project, process.job),
                }
            )
            for process in self.root.launcher.processes.values()
        )

    def prepare_finished(self):
        return "\n".join(
            self.prepare_row(
                {
                    "Project": escape(job.project),
                    "Spider": escape(job.spider),
                    "Job": escape(job.job),
                    "Start": no_microseconds(job.start_time),
                    "Runtime": no_microseconds(job.end_time - job.start_time),
                    "Finish": no_microseconds(job.end_time),
                    "Log": self.html_log_url(job),
                    "Items": self.html_item_url(job),
                }
            )
            for job in self.root.launcher.finished
        )

    def render_GET(self, txrequest):
        self.base_path = self.get_base_path(txrequest)

        content = dedent(
            f"""\
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Scrapyd</title>
                <style>
                    body {{ font-family: system-ui, sans-serif; }}
                    table {{ border-collapse: collapse; }}
                    th, td {{ border-style: solid; border-width: 1px; }}
                    tbody > tr:first-child {{ background-color: #eee; }}
                    th, td {{ padding: .5rem; }}
                    td:nth-child(2), td:nth-child(3) {{ word-break: break-all; }}
                </style>
            </head>
            <body>
                <h1>Jobs</h1>
                <p><a href="./">Go up</a></p>
                <table id="jobs">
                    <thead>
{indent(self.prepare_headers(), "                        ")}
                    </thead>
                    <tbody>
                        <tr>
                            <th colspan="{len(self.headers)}">Pending</th>
                        </tr>
{indent(self.prepare_pending(), "                        ")}
                    </tbody>
                    <tbody>
                        <tr>
                            <th colspan="{len(self.headers)}">Running</th>
                        </tr>
{indent(self.prepare_running(), "                        ")}
                    </tbody>
                    <tbody>
                        <tr>
                            <th colspan="{len(self.headers)}">Finished</th>
                        </tr>
{indent(self.prepare_finished(), "                        ")}
                    </tbody>
                </table>
            </body>
            </html>
            """
        ).encode()

        txrequest.setHeader("Content-Type", "text/html; charset=utf-8")
        txrequest.setHeader("Content-Length", str(len(content)))
        return content
