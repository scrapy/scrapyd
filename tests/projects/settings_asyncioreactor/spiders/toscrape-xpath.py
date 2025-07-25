import scrapy


class ToScrapeSpiderXPath(scrapy.Spider):
    name = "toscrape-xpath"

    def __init__(self, *args, **kwargs):
        self.start_urls = [kwargs["start_url"]]

    def parse(self, response):
        for quote in response.xpath('//div[@class="quote"]'):
            yield {
                "text": quote.xpath('./span[@class="text"]/text()').extract_first(),
                "author": quote.xpath('.//small[@class="author"]/text()').extract_first(),
                "tags": quote.xpath('.//div[@class="tags"]/a[@class="tag"]/text()').extract(),
            }

        next_page_url = response.xpath('//li[@class="next"]/a/@href').extract_first()
        if next_page_url is not None:
            yield scrapy.Request(response.urljoin(next_page_url))
