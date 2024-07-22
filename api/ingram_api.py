import asyncio
import aiohttp
import json
from config import DefaultConfig
from uuid import uuid4
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from aiohttp import ClientTimeout
import logging
import spacy
from nltk.stem import PorterStemmer, WordNetLemmatizer
from fuzzywuzzy import fuzz
import nltk

CONFIG = DefaultConfig()

class IngramAPI:
    def __init__(self):
        self.access_token = None
        self.token_expire_time = None
        self.nlp = spacy.load("en_core_web_sm")
        self.stemmer = PorterStemmer()
        self.lemmatizer = WordNetLemmatizer()
        nltk.download('wordnet', quiet=True)

    async def ensure_access_token(self):
        if not self.access_token or asyncio.get_running_loop().time() > self.token_expire_time:
            self.access_token, self.token_expire_time = await self.get_access_token()
            if not self.access_token:
                raise Exception("Unable to retrieve a valid token")

    async def get_access_token(self):
        url = "https://api.ingrammicro.com:443/oauth/oauth30/token"
        payload = {
            'grant_type': 'client_credentials',
            'client_id': CONFIG.INGRAM_CLIENT_ID,
            'client_secret': CONFIG.INGRAM_CLIENT_SECRET
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=payload, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    expire_time = asyncio.get_running_loop().time() + int(data['expires_in']) - 300
                    return data['access_token'], expire_time
                else:
                    logging.error(f"Failed to obtain access token: {response.status}, {await response.text()}")
                    return None, None

    def understand_intent(self, query):
        doc = self.nlp(query)
        product_types = [token.text for token in doc if token.pos_ == "NOUN"]
        brands = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
        return {"product_types": product_types, "brands": brands}

    def preprocess_keywords(self, keywords):
        words = keywords.lower().split()
        stemmed = [self.stemmer.stem(word) for word in words]
        lemmatized = [self.lemmatizer.lemmatize(word) for word in words]
        return set(stemmed + lemmatized)

    def fuzzy_match(self, query, product_name, threshold=80):
        return fuzz.partial_ratio(query.lower(), product_name.lower()) >= threshold

    def filter_available_products(self, products):
        available_products = [product for product in products if self.is_product_available(product)]
        logging.info(f"Total products: {len(products)}, Available products: {len(available_products)}")
        return available_products
    
    def is_product_available(self, product):
        availability = product.get('availability', {})
        logging.debug(f"Checking availability for product: {product.get('ingramPartNumber', 'N/A')}")
        logging.debug(f"Availability data: {availability}")
        
        if isinstance(availability, dict):
            available = availability.get('available')
            total_availability = availability.get('totalAvailability')
            logging.debug(f"Available: {available}, Total Availability: {total_availability}")
            
            if isinstance(available, bool):
                is_available = available or (total_availability is not None and total_availability > 0)
            elif isinstance(available, str):
                is_available = available.lower() in ['yes', 'true'] or (total_availability is not None and total_availability > 0)
            else:
                is_available = total_availability is not None and total_availability > 0
        else:
            is_available = False
        
        logging.debug(f"Product {product.get('ingramPartNumber', 'N/A')} is available: {is_available}")
        return is_available

    async def fetch_products(self, keywords):
        await self.ensure_access_token()
        url = 'https://api.ingrammicro.com:443/sandbox/resellers/v6/catalog'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'IM-CustomerNumber': CONFIG.INGRAM_CUSTOMER_NUMBER,
            'IM-SenderID': 'MyCompany',
            'IM-CorrelationID': str(uuid4())[:32],
            'IM-CountryCode': 'US',
            'Accept-Language': 'en',
            'Content-Type': 'application/json',
        }
        params = {
            'pageNumber': 1,
            'pageSize': 10,
            'type': 'IM::any',
            'keyword': keywords,
            'includeProductAttributes': 'true',
            'includePricing': 'true',
            'includeAvailability': 'true'
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, params=params, timeout=30) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        data = await response.json()
                        products = data.get('catalog', [])
                        logging.debug(f"Fetched {len(products)} products")
                        
                        products_with_availability = []
                        for product in products:
                            logging.debug(f"Product {product.get('ingramPartNumber', 'N/A')}: {product}")
                            availability = await self.fetch_price_and_availability(product.get('ingramPartNumber', ''))
                            product['availability'] = availability.get('availability', {})
                            products_with_availability.append(product)
                            logging.debug(f"Product {product['ingramPartNumber']} availability: {availability}")
                        
                        return products_with_availability
                    else:
                        logging.error(f"Failed API Call for keyword '{keywords}': {response.status}, {response_text}")
                        return []
            except asyncio.TimeoutError:
                logging.error("Request timed out")
                return []                

    def filter_and_score_products_by_keywords(self, products, query):
        intent = self.understand_intent(query)
        processed_keywords = self.preprocess_keywords(query)
        
        scored_products = []
        for product in products:
            score = 0
            product_text = (
                product.get('description', '').lower() +
                product.get('category', '').lower() +
                product.get('subCategory', '').lower() +
                product.get('productType', '').lower()
            )
            
            # Check for exact matches
            score += sum(keyword in product_text for keyword in processed_keywords) * 10
            
            # Check for fuzzy matches
            score += sum(self.fuzzy_match(keyword, product_text) for keyword in processed_keywords) / 10
            
            # Check for brand matches
            if any(brand.lower() in product.get('vendorName', '').lower() for brand in intent['brands']):
                score += 50
            
            # Check for product type matches
            if any(ptype.lower() in product_text for ptype in intent['product_types']):
                score += 30
            
            if score > 0:
                scored_products.append((score, product))
        
        # Sort products by score in descending order
        scored_products.sort(key=lambda x: x[0], reverse=True)
        
        # Return only the products, not the scores
        return [product for score, product in scored_products]
        
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(5), retry=retry_if_exception_type(asyncio.TimeoutError))
    async def fetch_price_and_availability(self, ingram_part_number):
        await self.ensure_access_token()
        base_url = 'https://api.ingrammicro.com:443/sandbox/resellers/v6/catalog/priceandavailability'

        params = {
            "includeAvailability": "true",
            "includePricing": "true",
            "includeProductAttributes": "true"
        }

        url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'accept': 'application/json',
            'IM-CustomerNumber': CONFIG.INGRAM_CUSTOMER_NUMBER,
            'IM-CountryCode': 'US',
            'IM-CorrelationID': str(uuid4())[:32],
            'IM-SenderID': 'MyCompany',
            'Content-Type': 'application/json'
        }

        payload = {
            "products": [
                {
                    "ingramPartNumber": ingram_part_number.upper()
                }
            ]
        }

        logging.debug(f"Request URL: {url}")
        logging.debug(f"Request Headers: {headers}")
        logging.debug(f"Request Payload: {payload}")

        timeout = ClientTimeout(total=30)  # Increased timeout to 30 seconds

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    response_text = await response.text()
                    logging.debug(f"Response Status: {response.status}")
                    logging.debug(f"Response Text: {response_text}")
                    if response.status == 200:
                        product_details = await response.json()
                        # The response is a list, so we need to access the first item
                        if isinstance(product_details, list) and len(product_details) > 0:
                            return product_details[0]  # Return the entire product details
                        else:
                            return {}
                    else:
                        logging.error(f"Failed to fetch availability for {ingram_part_number}: {response.status}")
                        return {}
            except asyncio.TimeoutError:
                logging.error(f"Request timed out for part number: {ingram_part_number}")
                raise
            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                logging.error(error_msg)
                raise  # Re-raise the exception to be caught by the retry decorator

    def format_product_details(self, product_details):
        logging.debug(f"Received product details: {product_details}")

        if not product_details:
            return "No product details found."

        formatted_products = []
        for product in product_details:
            ingram_part_number = product.get('ingramPartNumber', 'N/A')
            vendor_part_number = product.get('vendorPartNumber', 'N/A')
            description = product.get('description', 'N/A')
            upc = product.get('upc', 'None')
            vendor_name = product.get('vendorName', 'None')
            availability = product.get('availability', {})
            pricing = product.get('pricing', {})

            availability_by_warehouse = availability.get('availabilityByWarehouse', [])
            if availability_by_warehouse is None:
                availability_by_warehouse = []

            availability_details = "\n".join(
                [f"Warehouse: {wh.get('location', 'N/A')}, Quantity Available: {wh.get('quantityAvailable', 'N/A')}"
                 for wh in availability_by_warehouse]
            )

            response = (
                f"**Ingram Part Number:** {ingram_part_number}  \n"
                f"**Vendor Part Number:** {vendor_part_number}  \n"
                f"**Description:** {description}  \n"
                f"**UPC:** {upc}  \n"
                f"**Vendor Name:** {vendor_name}  \n"
                f"**Available:** {'Yes' if availability.get('available') else 'No'}  \n"
                f"**Total Availability:** {availability.get('totalAvailability', 'N/A')}  \n"
                f"**Availability by Warehouse:**\n{availability_details}  \n"
                f"**Retail Price:** {pricing.get('retailPrice', 'N/A')} {pricing.get('currencyCode', 'USD')}  \n"
                f"**Customer Price:** {pricing.get('customerPrice', 'N/A')} {pricing.get('currencyCode', 'USD')}  \n"
            )

            formatted_products.append(response)

        return "\n\n".join(formatted_products)