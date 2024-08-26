from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from unidecode import unidecode
import scrapy
import json
import datetime

# database constants
DB_NAME = "PhongVu"
COLLECTION_PRODUCT = "products"
COLLECTION_PRICES = "prices"

class ProductSpider(scrapy.Spider):
    name = "product"
    allowed_domains = ["phongvu.vn"]
    start_urls = [
        "https://phongvu.vn/"
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 5,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    }

    def __init__(self, *args, **kwargs):
        super(ProductSpider, self).__init__(*args, **kwargs)
        self.max_requests = 15000  # Maximum number of requests
        self.request_count = 0
        self.product_count = 0
        self.start_time = datetime.datetime.now()

        try:
            with open('./login.json') as f:
                login = json.load(f)
                username = login['username']
                password = login['password']
                cluster = login['cluster@']
        except (FileNotFoundError, KeyError) as e:
            self.crawler.engine.close_spider(self, 'Failed to connect to MongoDB')
        
        uri = f"mongodb+srv://{username}:{password}@{cluster}"

        # Create a new client and connect to the server
        self.client = MongoClient(uri, server_api=ServerApi('1'))

        # Send a ping to confirm a successful connection
        try:
            self.client.admin.command('ping')
            self.log("Successfully connected to MongoDB!")
        except Exception as e:
            self.log(e)
            self.crawler.engine.close_spider(self, 'Failed to connect to MongoDB')

        db = self.client[DB_NAME]
        self.collection_product = db[COLLECTION_PRODUCT]
        self.collection_prices = db[COLLECTION_PRICES]
    
    def normalize(self, text):
        #remove all accents, special characters
        return unidecode(text).lower()
    
    def is_hang_trung_bay(self, text):
        #check if normalized text contains "trung bay"
        return "trung bay" in self.normalize(text)
    
    def parse(self, response):
        # Increment the request count
        self.request_count += 1

        # Check if the request count exceeds the maximum
        if self.request_count > self.max_requests:
            self.crawler.engine.close_spider(self, 'Reached maximum request limit')
            return
        
        # Try to extract product information
        script = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if script:
            try:
                product_script_json = json.loads(script)
                product_script_data = product_script_json['props']['pageProps']['serverProduct']['product']
                product_info = product_script_data['productInfo']
                product_prices = product_script_data['prices'][0]

                # Serialize product info
                product_info_serialize = {
                    '_id': product_info['sku'],
                    'name': product_info['name'],
                    'name_normalized': self.normalize(product_info['name']),
                    'image': product_info['imageUrl'],
                    'brand': product_info['brand']['name'],
                    'url': response.url,
                    'demo' : self.is_hang_trung_bay(self.normalize(product_info['name'])),
                    'last_update': datetime.datetime.now().strftime('%Y-%m-%d')
                }

                # Serialize product prices
                product_prices_serialize = {
                    'sku': product_info['sku'],
                    'date': datetime.datetime.now().strftime('%Y-%m-%d'),
                    'price (VND)': int(product_prices['latestPrice']),
                    'retail price (VND)': int(product_prices['supplierRetailPrice']),
                    'discount (%)': float(product_prices['discountPercent'])
                }
                self.product_count += 1

                # Insert the data into the MongoDB collection
                try:
                    result = self.collection_product.update_one({'_id': product_info['sku']}, {'$set': product_info_serialize}, upsert=True)
                except Exception as e:
                    print(f"An error occurred: {e}")

                try:
                    result = self.collection_prices.insert_one(product_prices_serialize)
                except Exception as e:
                    print(f"An error occurred: {e}")

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                self.log(f"Error: {e} at {response.url}")

        # Follow all links on the page
        links = response.xpath('//a/@href').extract()
        for link in links:
            yield response.follow(link, self.parse)

    def closed(self, reason):
        self.end_time = datetime.datetime.now()
        self.log(f"Time elapsed: {self.end_time - self.start_time}")
        self.log(f"Total number of products parsed: {self.product_count}")

        with open ('./last_run.txt', 'w') as f:
            f.write(f"Time started: {self.start_time}\n")
            f.write(f"Time elapsed: {self.end_time - self.start_time}\n")
            f.write(f"Total number of products parsed: {self.product_count}\n")


        self.client.close()