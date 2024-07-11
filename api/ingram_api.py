import asyncio
import aiohttp
import json
from config import DefaultConfig
from uuid import uuid4
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from aiohttp import ClientTimeout
import logging

CONFIG = DefaultConfig()

class IngramAPI:
    def __init__(self):
        self.access_token = None
        self.token_expire_time = None

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
            'pageSize': 50,
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
                        return data.get('catalog', [])
                    else:
                        logging.error(f"Failed API Call for keyword '{keywords}': {response.status}, {response_text}")
                        return []
            except asyncio.TimeoutError:
                logging.error("Request timed out")
                return []

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
                        return product_details
                    else:
                        error_msg = f"Failed to fetch details: {response.status} - {response_text}"
                        logging.error(error_msg)
                        return error_msg
            except asyncio.TimeoutError:
                logging.error(f"Request timed out for part number: {ingram_part_number}")
                raise
            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                logging.error(error_msg)
                raise  # Re-raise the exception to be caught by the retry decorator

    def format_product_details(self, product_details):
        logging.debug(f"Received product details: {product_details}")
    
        if isinstance(product_details, list):
            if not product_details:
                return "No product details found."
            products = product_details
        elif isinstance(product_details, dict):
            products = product_details.get('priceAndAvailabilityResponse', {}).get('products', [])
        else:
            return f"Invalid product data format: {type(product_details)}"
    
        if not products:
            return "No product details found."

        formatted_products = []
        for product in products:
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
                f"**Ingram Part Number:** {product.get('ingramPartNumber', 'N/A')}  \n"
                f"**Vendor Part Number:** {product.get('vendorPartNumber', 'N/A')}  \n"
                f"**Description:** {product.get('description', 'N/A')}  \n"
                f"**UPC:** {product.get('upc', 'N/A')}  \n"
                f"**Vendor Name:** {product.get('vendorName', 'N/A')}  \n"
                f"**Available:** {'Yes' if availability.get('available') else 'No'}  \n"
                f"**Total Availability:** {availability.get('totalAvailability', 'N/A')}  \n"
                f"**Availability by Warehouse:**\n{availability_details}  \n"
                f"**Retail Price:** {pricing.get('retailPrice', 'N/A')} {pricing.get('currencyCode', 'USD')}  \n"
                f"**Customer Price:** {pricing.get('customerPrice', 'N/A')} {pricing.get('currencyCode', 'USD')}  \n"
            )

            formatted_products.append(response)

        return "\n\n".join(formatted_products)