
import posixpath
import pkg_resources

from twisted.web import resource, static
from twisted.web.util import Redirect

class EmptyFrontEnd(resource.Resource):
    def __init__(self, root):
        resource.Resource.__init__(self)
        self.root = root

    def render(self, request, **kwargs):
        request.setResponseCode(404)
        return """<html><head><title>No frontend</title><h1>No frontend</h1>
        </body>
        </html>
        """

class FrontEnd(EmptyFrontEnd):
    def __init__(self, root, **kwargs):
        EmptyFrontEnd.__init__(self, root, **kwargs)

        cfg = dict(root.config.items("frontend", ()))
        self.path = cfg.get("path", 
            pkg_resources.resource_filename("scrapyd", "frontend/site"))

    def render(self, request, **kwargs):
        if not posixpath.exists(self.path):
            request.setResponseCode(404)
            return "Path not found"

        path = "/index.html" if request.path == "/" else request.path
        r = posixpath.join(self.path, 
            path[1:] if path.startswith("/") else path)
        return static.File(r).render(request, **kwargs)
