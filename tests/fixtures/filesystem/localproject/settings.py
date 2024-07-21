BOT_NAME = "localproject"
SPIDER_MODULES = ["localproject.spiders"]
NEWSPIDER_MODULE = "localproject.spiders"
ROBOTSTXT_OBEY = True
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
