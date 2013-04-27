import posixpath
import pkg_resources

from twisted.web import resource, static
from twisted.web.util import Redirect

class BaseFrontEnd(resource.Resource):
    def __init__(self, root):
        resource.Resource.__init__(self)
        self.root = root

    def render(self, request, **kwargs):
        request.setResponseCode(404)
        return """<html><head><title>No frontend</title><h1>No frontend</h1>
        </body>
        </html>
        """

class FrontEnd(resource.Resource):
    document_index = "index.html"
    
    def __init__(self, root, path=None, **kwargs):
        self.root = root
        self.path = (path or posixpath.expanduser(self.root.config.get("htdocs_dir")) or 
            pkg_resources.resource_filename("scrapyd", "frontend/site"))
        resource.Resource.__init__(self, **kwargs)

    def render(self, request, **kwargs):
        if not posixpath.exists(self.path):
            request.setResponseCode(404)
            return "Path not found"
    
        path = ("/%s" % self.document_index if request.path == "/" 
                    else request.path)
        r = posixpath.join(self.path, 
            path[1:] if path.startswith("/") else path)
        return static.File(r).render(request, **kwargs)
