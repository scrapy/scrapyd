from scrapy.spiders import Spider


class Spider1(Spider):
    name = "error"

    import importerror  # noqa: PLC0415
