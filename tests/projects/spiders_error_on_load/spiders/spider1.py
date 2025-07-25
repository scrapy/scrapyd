from scrapy.spiders import Spider


class Spider1(Spider):
    name = "error"

    def start_requests(self):
        import importerror  # noqa: F401, PLC0415
