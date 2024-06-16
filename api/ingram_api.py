import asyncio
import aiohttp
import json
from config import DefaultConfig
from uuid import uuid4

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
            async with session.post(url, headers=headers, data=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    expire_time = asyncio.get_running_loop().time() + int(data['expires_in']) - 300
                    return data['access_token'], expire_time
                else:
                    print(f"Failed to obtain access token: {response.status}, {await response.text()}")
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
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('catalog', [])
                else:
                    print(f"Failed API Call for keyword '{keywords}': {response.status}, {await response.text()}")
                    return []

    async def fetch_price_and_availability(self, ingram_part_number):
        await self.ensure_access_token()
        url = (f'https://api.ingrammicro.com:443/sandbox/resellers/v6/catalog/priceandavailability'
            f'?includePricing=true&includeAvailability=true&includeProductAttributes=true')

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'IM-CustomerNumber': CONFIG.INGRAM_CUSTOMER_NUMBER,
            'IM-CountryCode': 'US',
            'IM-CorrelationID': str(uuid4())[:32],
            'IM-SenderID': 'MyCompany',
            'Accept': 'application/json'
        }

        data = json.dumps({"products": [{"ingramPartNumber": ingram_part_number.upper()}]})

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as response:
                if response.status == 200:
                    product_details = await response.json()
                    print(f"Raw response data: {product_details}")
                    return self.format_product_details(product_details)
                else:
                    error_message = await response.text()
                    print(f"Failed to fetch details: {response.status} - {error_message}")
                    return f"Failed to fetch details: {response.status} - {error_message}"

    def format_product_details(self, product_details):
        print(f"Raw product details: {product_details}")

        if not isinstance(product_details, list) or not product_details:
            print("Invalid product data format or empty products list.")
            return "Invalid product data format."

        formatted_products = []
        for product in product_details:
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
