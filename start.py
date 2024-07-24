import json
from scrapy.crawler import CrawlerProcess
from phongvu_scraper.spiders.product import ProductSpider

with open('./login.json') as f:
    login = json.load(f)
    username = login['username']
    password = login['password']
    cluster = login['cluster@']
    if len(username) == 0 or len(password) == 0 or len(cluster) == 0:
        print("Invalid login credentials")
        exit()

process = CrawlerProcess()
process.crawl(ProductSpider)
process.start()