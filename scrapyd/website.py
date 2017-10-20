from datetime import datetime

import socket, json

from twisted.web import resource, static
from twisted.application.service import IServiceCollection

from scrapy.utils.misc import load_object

from .interfaces import IPoller, IEggStorage, ISpiderScheduler

from six.moves.urllib.parse import urlparse

class Root(resource.Resource):

    def __init__(self, config, app):
        resource.Resource.__init__(self)
        self.debug = config.getboolean('debug', False)
        self.runner = config.get('runner')
        logsdir = config.get('logs_dir')
        itemsdir = config.get('items_dir')
        local_items = itemsdir and (urlparse(itemsdir).scheme.lower() in ['', 'file'])
        self.app = app
        self.nodename = config.get('node_name', socket.gethostname())
        self.putChild(b'', Home(self, local_items))
        if logsdir:
            self.putChild(b'logs', static.File(logsdir.encode('ascii', 'ignore'), 'text/plain'))
        if local_items:
            self.putChild(b'items', static.File(itemsdir, 'text/plain'))
        self.putChild(b'jobs', Jobs(self, local_items))
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


class Home(resource.Resource):

    def __init__(self, root, local_items):
        resource.Resource.__init__(self)
        self.root = root
        self.local_items = local_items

    def render_GET(self, txrequest):
        vars = {
            'projects': ', '.join(self.root.scheduler.list_projects())
        }
        s = """
<html>
<head><title>Scrapyd</title></head>
<body>
<h1>Scrapyd</h1>
<p>Available projects: <b>%(projects)s</b></p>
<ul>
<li><a href="/jobs">Jobs</a></li>
""" % vars
        if self.local_items:
            s += '<li><a href="/items/">Items</a></li>'
        s += """
<li><a href="/logs/">Logs</a></li>
<li><a href="http://scrapyd.readthedocs.org/en/latest/">Documentation</a></li>
</ul>

<h2>How to schedule a spider?</h2>

<p>To schedule a spider you need to use the API (this web UI is only for
monitoring)</p>

<p>Example using <a href="http://curl.haxx.se/">curl</a>:</p>
<p><code>curl http://localhost:6800/schedule.json -d project=default -d spider=somespider</code></p>

<p>For more information about the API, see the <a href="http://scrapyd.readthedocs.org/en/latest/">Scrapyd documentation</a></p>
</body>
</html>
""" % vars
        return s.encode('utf-8')

class Jobs(resource.Resource):

    def __init__(self, root, local_items):
        resource.Resource.__init__(self)
        self.root = root
        self.local_items = local_items

    def render(self, txrequest):
        cols = 0

        s = "<html><head><title>Scrapyd</title>"
        s += """
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
            <script>!function(){function n(n,t){for(property in t)t.hasOwnProperty(property)&&(n[property]=t[property]);return n}function t(n,t){var i=document.createElement("div");i.className="notyf";var e=document.createElement("div");e.className="notyf-wrapper";var o=document.createElement("div");o.className="notyf-icon";var a=document.createElement("i");a.className=t;var r=document.createElement("div");r.className="notyf-message",r.innerHTML=n,o.appendChild(a),e.appendChild(o),e.appendChild(r),i.appendChild(e);var c=this;return setTimeout(function(){i.className+=" disappear",i.addEventListener(c.animationEnd,function(n){n.target==i&&c.container.removeChild(i)});var n=c.notifications.indexOf(i);c.notifications.splice(n,1)},c.options.delay),i}function i(){var n,t=document.createElement("fake"),i={transition:"animationend",OTransition:"oAnimationEnd",MozTransition:"animationend",WebkitTransition:"webkitAnimationEnd"};for(n in i)if(void 0!==t.style[n])return i[n]}this.Notyf=function(){this.notifications=[];var t={delay:2e3,alertIcon:"notyf-alert-icon",confirmIcon:"notyf-confirm-icon"};arguments[0]&&"object"==typeof arguments[0]?this.options=n(t,arguments[0]):this.options=t;var e=document.createDocumentFragment(),o=document.createElement("div");o.className="notyf-container",e.appendChild(o),document.body.appendChild(e),this.container=o,this.animationEnd=i()},this.Notyf.prototype.alert=function(n){var i=t.call(this,n,this.options.alertIcon);i.className+=" alert",this.container.appendChild(i),this.notifications.push(i)},this.Notyf.prototype.confirm=function(n){var i=t.call(this,n,this.options.confirmIcon);i.className+=" confirm",this.container.appendChild(i),this.notifications.push(i)}}();</script>
            <style>@-webkit-keyframes a{0%{opacity:0;bottom:-15px;max-height:0;max-width:0;margin-top:0}30%{opacity:.8;bottom:-3px}to{opacity:1;bottom:0;max-height:200px;margin-top:12px;max-width:400px}}@keyframes a{0%{opacity:0;bottom:-15px;max-height:0;max-width:0;margin-top:0}30%{opacity:.8;bottom:-3px}to{opacity:1;bottom:0;max-height:200px;margin-top:12px;max-width:400px}}@-webkit-keyframes b{0%{opacity:1;bottom:0}30%{opacity:.2;bottom:-3px}to{opacity:0;bottom:-15px}}@keyframes b{0%{opacity:1;bottom:0}30%{opacity:.2;bottom:-3px}to{opacity:0;bottom:-15px}}@-webkit-keyframes c{0%{opacity:0}30%{opacity:.5}to{opacity:.6}}@keyframes c{0%{opacity:0}30%{opacity:.5}to{opacity:.6}}@-webkit-keyframes d{0%{opacity:.6}30%{opacity:.1}to{opacity:0}}@keyframes d{0%{opacity:.6}30%{opacity:.1}to{opacity:0}}.notyf-container{position:fixed;bottom:20px;right:30px;width:20%;color:#fff;z-index:1}.notyf-container .notyf-alert-icon,.notyf-container .notyf-confirm-icon{height:21px;width:21px;background:#fff;border-radius:50%;display:block;margin:0 auto;position:relative}.notyf-container .notyf-alert-icon:after,.notyf-container .notyf-alert-icon:before{content:"";background:#ed3d3d;display:block;position:absolute;width:3px;border-radius:3px;left:9px}.notyf-container .notyf-alert-icon:after{height:3px;top:14px}.notyf-container .notyf-alert-icon:before{height:8px;top:4px}.notyf-container .notyf-confirm-icon:after,.notyf-container .notyf-confirm-icon:before{content:"";background:#3dc763;display:block;position:absolute;width:3px;border-radius:3px}.notyf-container .notyf-confirm-icon:after{height:6px;-webkit-transform:rotate(-45deg);transform:rotate(-45deg);top:9px;left:6px}.notyf-container .notyf-confirm-icon:before{height:11px;-webkit-transform:rotate(45deg);transform:rotate(45deg);top:5px;left:10px}.notyf-container .notyf{display:block;overflow:hidden;-webkit-animation:a .3s forwards;animation:a .3s forwards;box-shadow:0 1px 3px 0 rgba(0,0,0,.45);position:relative;padding-right:13px}.notyf-container .notyf.alert{background:#ed3d3d}.notyf-container .notyf.confirm{background:#3dc763}.notyf-container .notyf.disappear{-webkit-animation:b .3s 1 forwards;animation:b .3s 1 forwards;-webkit-animation-delay:.25s;animation-delay:.25s}.notyf-container .notyf.disappear .notyf-message{opacity:1;-webkit-animation:b .3s 1 forwards;animation:b .3s 1 forwards;-webkit-animation-delay:.1s;animation-delay:.1s}.notyf-container .notyf.disappear .notyf-icon{opacity:1;-webkit-animation:d .3s 1 forwards;animation:d .3s 1 forwards}.notyf-container .notyf-wrapper{display:table;width:100%;padding-top:20px;padding-bottom:20px;padding-right:15px;border-radius:3px}.notyf-container .notyf-icon{display:table-cell;width:20%;text-align:center;vertical-align:middle;font-size:1.3em;opacity:0;-webkit-animation:c .5s forwards;animation:c .5s forwards;-webkit-animation-delay:.25s;animation-delay:.25s}.notyf-container .notyf-message{display:table-cell;width:80%;vertical-align:middle;position:relative;opacity:0;-webkit-animation:a .3s forwards;animation:a .3s forwards;-webkit-animation-delay:.15s;animation-delay:.15s}@media only screen and (max-width:736px){.notyf-container{width:90%;margin:0 auto;display:block;right:0;left:0}}</style>
        """
        s += "</head>"
        s += "<body>"
        s += "<h1>Jobs</h1>"
        s += "<p><a href='..'>Go back</a></p>"
        s += "<table border='1'>"
        starting_default_headers = ["Project", "Spider", "Job", "PID"]
        ending_default_headers = ["Start", "Runtime", "Finish", "Log"]
        ending_additional_headers = ["Action"]
        
        additional_headers = []
        for project, queue in self.root.poller.queues.items():
            for m in queue.list():
                for k, a in m.iteritems():
                    if k not in ['name', '_job']:
                        if type(a) is unicode or type(a) is str:
                            if k not in additional_headers:
                                additional_headers.extend([k])
                                
        for p in self.root.launcher.processes.values():
            temp = getattr(p, 'arguments')
            for key,value in enumerate(temp):
                if value == "-a":
                    argument_name = temp[key+1].split("=")[0]
                    if argument_name not in ['name', '_job'] and argument_name not in additional_headers:
                        additional_headers.extend([argument_name])
                        
        for p in self.root.launcher.finished:
            temp = getattr(p, 'arguments')
            for key,value in enumerate(temp):
                if value == "-a":
                    argument_name = temp[key+1].split("=")[0]
                    if argument_name not in ['name', '_job'] and argument_name not in additional_headers:
                        additional_headers.extend([argument_name])
                        
        if self.local_items:
            ending_default_headers.extend(["Items"])
            
        starting_default_headers = starting_default_headers + additional_headers + ending_default_headers + ending_additional_headers
            
        s += "<tr>"
        for header in starting_default_headers:
            s += "<th>"+header+"</th>"
            cols = cols+1

        s += "</tr>"

        s += "<tr><th colspan='%s' style='background-color: #ddd'>Pending</th></tr>" % cols
        for project, queue in self.root.poller.queues.items():
            for m in queue.list():
                s += "<tr>"
                s += "<td>%s</td>" % project
                s += "<td>%s</td>" % str(m['name'])
                s += "<td>%s</td>" % str(m['_job'])
                s += "<td></td>"
                
                for header in additional_headers:
                    s += "<td>%s</td>" % str(m[header] if header in m else "")

                for ending_header in ending_default_headers:
                    s += "<td></td>"
                                
                s += "<td><a style='cursor:pointer' onClick=stopJob('%s')>Stop</a></td>"%(m['_job'])
                s += "</tr>"
                
        s += "<tr><th colspan='%s' style='background-color: #ddd'>Running</th></tr>" % cols
        for p in self.root.launcher.processes.values():
            s += "<tr>"
            for a in ['project', 'spider', 'job', 'pid']:
                s += "<td>%s</td>" % getattr(p, a)
                
            temp = getattr(p, 'arguments')
            additional_headers_values = {}
            for key,value in enumerate(temp):
                if value == "-a":
                    argument_name = temp[key+1].split("=")[0]
                    if argument_name not in ['name', '_job'] and argument_name not in additional_headers_values:
                            additional_headers_values[temp[key+1].split("=")[0]] = "".join(temp[key+1].split("=")[1:])
               
            for header in additional_headers:
                s += "<td>%s</td>" % str(additional_headers_values[header] if header in additional_headers_values else "")
                
            s += "<td>%s</td>" % p.start_time.replace(microsecond=0)
            s += "<td>%s</td>" % (datetime.now().replace(microsecond=0) - p.start_time.replace(microsecond=0))
            s += "<td></td>"
            s += "<td><a href='/logs/%s/%s/%s.log'>Log</a></td>" % (p.project, p.spider, p.job)
            if self.local_items:
                s += "<td><a href='/items/%s/%s/%s.jl'>Items</a></td>" % (p.project, p.spider, p.job)
                
            s += "<td><a style='cursor:pointer' onClick=stopJob('%s')>Stop</a></td>"%(p.job)
                
            s += "</tr>"
        s += "<tr><th colspan='%s' style='background-color: #ddd'>Finished</th></tr>" % cols

        for p in self.root.launcher.finished:
            s += "<tr>"
            for a in ['project', 'spider', 'job']:
                s += "<td>%s</td>" % getattr(p, a)
            s += "<td></td>"
            
            temp = getattr(p, 'arguments')
            additional_headers_values = {}
            for key,value in enumerate(temp):
                if value == "-a":
                    argument_name = temp[key+1].split("=")[0]
                    if argument_name not in ['name', '_job'] and argument_name not in additional_headers_values:
                            additional_headers_values[temp[key+1].split("=")[0]] = "".join(temp[key+1].split("=")[1:])
               
            for header in additional_headers:
                s += "<td>%s</td>" % str(additional_headers_values[header] if header in additional_headers_values else "")
            
            s += "<td>%s</td>" % p.start_time.replace(microsecond=0)
            s += "<td>%s</td>" % (p.end_time.replace(microsecond=0) - p.start_time.replace(microsecond=0))
            s += "<td>%s</td>" % p.end_time.replace(microsecond=0)
            s += "<td><a href='/logs/%s/%s/%s.log'>Log</a></td>" % (p.project, p.spider, p.job)
            if self.local_items:
                s += "<td><a href='/items/%s/%s/%s.jl'>Items</a></td>" % (p.project, p.spider, p.job)
            s += "</tr>"
        s += "</table>"
        
        s += """
            <script>
            var notyf;
            (function(){
            notyf = new Notyf({delay:3000});
            })();
            function stopJob(job){
            
                    $.post("cancel.json",
                    {
                      project: "default",
                      job: job
                    },
                    function(data,status){
                        if (data.status=="ok"){
                            notyf.confirm("Job successfully stopped");
                        }else{
                            notyf.alert("There was some error stopping, please contact your developer");
                        }
                    });
            }
            </script>
        
        """
        
        s += "</body>"
        s += "</html>"

        txrequest.setHeader('Content-Type', 'text/html; charset=utf-8')
        txrequest.setHeader('Content-Length', len(s))

        return s.encode("utf-8")
