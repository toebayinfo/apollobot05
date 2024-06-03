def format_response(products, query_terms):
    formatted_products = []
    for product_data in products:
        for product in product_data.get('catalog', []):
            # Check if product attributes exist and have valid values
            product_name = product.get('vendorName', '').lower() if product.get('vendorName') else ''
            product_description = product.get('description', '').lower() if product.get('description') else ''
            product_category = product.get('category', '').lower() if product.get('category') else ''
            product_type = product.get('productType', '').lower() if product.get('productType') else ''
            
            # Ensure the product is a Dell product
            if 'dell' in product_name or 'dell' in product_description:
                # Check if the product matches the specific category requested
                if 'notebook' in query_terms or 'laptop' in query_terms:
                    if ('notebook' in product_type or 'laptop' in product_type or 'portable computer' in product_category) and not ('accessory' in product_category or 'battery' in product_type or 'charger' in product_type or 'adapter' in product_type):
                        formatted_products.append(format_product(product))
                elif 'battery' in query_terms:
                    if 'battery' in product_type or 'battery' in product_description:
                        formatted_products.append(format_product(product))
                else:
                    formatted_products.append(format_product(product))
    return "\n\n".join(formatted_products)

def format_product(product):
    links_info = "No direct link available"
    if 'links' in product and product['links']:
        link = next((link for link in product['links'] if link.get('type') == 'GET'), None)
        links_info = link['href'] if link else links_info
    description = product.get('description', 'No description available')
    category = product.get('category', 'No category')
    vendor_name = product.get('vendorName', 'No vendor name')
    vendorPartNumber = product.get('vendorPartNumber', 'No vendor Part number')
    extraDescription = product.get('extraDescription', 'No Extended Description available')
    subCategory = product.get('subCategory', 'No subcategory')
    productType = product.get('productType', 'No product type')
    formatted_product = f"**Product Details:** {vendor_name} - {description}  \n**Category:** {category} - {subCategory}  \n**Product Type:** {productType}  \n**Price and availability information:** {links_info}"
    return formatted_product

def format_product_details(product_details):
    formatted_products = []
    for product in product_details:
        ingram_part_number = product.get('ingramPartNumber', 'N/A').upper()
        description = product.get('description', 'No description available')
        product_status_code = product.get('productStatusCode', 'N/A')
        product_status_message = product.get('productStatusMessage', 'No status message available')

        availability = product.get('availability', {})
        available = availability.get('available', False)
        total_availability = availability.get('totalAvailability', 0)

        pricing = product.get('pricing', {})
        retail_price = pricing.get('retailPrice', 'N/A')
        customer_price = pricing.get('customerPrice', 'N/A')

        formatted_product = (
            f"**Product Number:** {ingram_part_number}  \n "
            f"**Product Status Code:** {product_status_code} -  \n {product_status_message}  \n "
            f"**Description:** {description}  \n "
            f"**Availability:** {'Available' if available else 'Not Available'}  \n "
            f"**Total Availability:** {total_availability}  \n "
            f"**Retail Price:** {retail_price}  \n "
            f"**Customer Price:** {customer_price}"
        )
        formatted_products.append(formatted_product)

    return "\n\n".join(formatted_products)