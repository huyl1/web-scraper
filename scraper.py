import json
import requests
from bs4 import BeautifulSoup
import re
import datetime

URL = "https://phongvu.vn/man-hinh-lcd-dell-24-u2424ht--s240103543"

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}

page = requests.get(URL, headers=headers)

soup = BeautifulSoup(page.content, "html.parser")

# script
product_script = soup.find('script', id="__NEXT_DATA__")
product_script_json = json.loads(product_script.string)
product_script_data = product_script_json['props']['pageProps']['serverProduct']['product']

product_info = product_script_data['productInfo']
product_prices = product_script_data['prices'][0]

product_info_serialize = {
    '_id': product_info['sku'],
    'name': product_info['name'],
    'image': product_info['imageUrl'],
    'brand': product_info['brand']['name'],
    'url': URL
}

product_prices_serialize = {
    'sku': product_info['sku'],
    'date': datetime.datetime.now().strftime('%Y-%m-%d'),
    'price (VND)': product_prices['sellPrice'],
    'retail price (VND)': product_prices['supplierRetailPrice'],
    'discount (%)': product_prices['discountPercent']
}


from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# fetch login from login.json
with open('login.json') as f:
    login = json.load(f)

username = login['username']
password = login['password']

uri = "mongodb+srv://" + username + ":" + password + "@cluster0.oxoi2sh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client['PhongVu']
collection_product = db["Product Data"]
collection_prices = db["Price Data"]

# Insert the data into the MongoDB collection
try:
    result = collection_product.update_one({'_id': product_info['sku']}, {'$set': product_info_serialize}, upsert=True)
    if result.upserted_id is not None:
        print(f"Document inserted with _id: {result.upserted_id}")
    elif result.modified_count > 0:
        print(f"Document with _id {product_info['sku']} updated.")
    else:
        print("No changes made to the document.")
except Exception as e:
    print(f"An error occurred: {e}")

try:
    result = collection_prices.insert_one(product_prices_serialize)
    print(f"Price inserted with _id: {result.inserted_id}")
except Exception as e:
    print(f"An error occurred: {e}")

client.close()