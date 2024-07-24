import json
from time import sleep
from scrapy.crawler import CrawlerProcess
from phongvu_scraper.spiders.product import ProductSpider

while True:
    with open('./login.json') as f:
        login = json.load(f)
        username = login['username']
        password = login['password']
        cluster = login['cluster@']
        if len(username) == 0 or len(password) == 0 or len(cluster) == 0:
            print('Please fill in the login.json file')
            sleep(1)
            continue
        else:
            break

process = CrawlerProcess()
process.crawl(ProductSpider)
process.start()