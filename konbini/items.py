# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class KonbiniItem(scrapy.Item):
    # define the fields for your item here like:
    title = scrapy.Field()
    author = scrapy.Field()
    journal = scrapy.Field()
    year = scrapy.Field()
    abstract = scrapy.Field()
    pdf = scrapy.Field()
    url = scrapy.Field()
    if_download = scrapy.Field()
    citation = scrapy.Field()
    pass
