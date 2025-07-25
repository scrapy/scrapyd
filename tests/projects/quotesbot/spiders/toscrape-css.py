import scrapy


class ToScrapeCSSSpider(scrapy.Spider):
    name = "toscrape-css"

    def __init__(self, *args, **kwargs):
        self.start_urls = [kwargs["start_url"]]

    def parse(self, response):
        for quote in response.css("div.quote"):
            yield {
                "text": quote.css("span.text::text").extract_first(),
                "author": quote.css("small.author::text").extract_first(),
                "tags": quote.css("div.tags > a.tag::text").extract(),
            }

        next_page_url = response.css("li.next > a::attr(href)").extract_first()
        if next_page_url is not None:
            yield scrapy.Request(response.urljoin(next_page_url))
