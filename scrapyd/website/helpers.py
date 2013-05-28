import posixpath
import pkgutil
import pkg_resources

from twisted.web import resource

class Favorite(resource.Resource):
    isLeaf = True

    def __init__(self, root, **kwargs):
        self.root = root
        
    def render(self, request):
        request.setHeader("Content-Type", "image/x-icon")
        data = pkgutil.get_data("scrapyd.website", "img/favicon.ico")
        return data

class AppleTouch(resource.Resource):
    isLeaf = True

    def __init__(self, root, **kwargs):
        self.root = root

    def render(self, request):
        request.setHeader("Content-Type", "image/png")
        data = pkgutil.get_data("scrapyd.website", "img/apple-touch-icon.png")
        return data

class Robots(resource.Resource):
    isLeaf = True

    def __init__(self, root, **kwargs):
        self.root = root

    def render(self, request):
        request.setHeader("Content-Type", "text/pplain")
        return """User-agent: *\nDisallow: /\n"""
