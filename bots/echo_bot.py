import asyncio
import re
import traceback
from botbuilder.core import ActivityHandler, TurnContext, ConversationState
from botbuilder.schema import Activity
from api.ingram_api import IngramAPI
from api.openai_api import OpenAIAPI
from api.excel_api import ExcelAPI
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CustomEchoBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState):
        self.ingram_api = IngramAPI()
        self.openai_api = OpenAIAPI()
        self.conversation_state = conversation_state
        self.user_state_accessor = self.conversation_state.create_property("UserState")
        self.welcomed_user_ids = set()
        self.excel_api = ExcelAPI()
        self.excel_data = None

    async def on_turn(self, turn_context: TurnContext):
        try:
            if self.excel_data is None:
                self.excel_data = await self.excel_api.get_excel_data()
            await super().on_turn(turn_context)
        except Exception as e:
            print(f"Exception in on_turn: {str(e)}")
            traceback.print_exc()
            await turn_context.send_activity("An unexpected error occurred.")
        finally:
            await self.conversation_state.save_changes(turn_context)

    async def on_message_activity(self, turn_context: TurnContext):
        try:
            user_state = await self.user_state_accessor.get(turn_context, dict)
            await self.ingram_api.ensure_access_token()
            user_message = turn_context.activity.text.lower()
            # Replace "laptop" with "notebook" in the user's message
            user_message = user_message.replace("laptop", "notebook")

            keyword_search = re.search(r"search product details for (.+)", user_message)
            product_id_search = re.search(r"price and availability for (\w+)", user_message)

            if keyword_search:
                query = keyword_search.group(1)
                user_state['last_query'] = query
                
                products_data = await self.ingram_api.fetch_products(query)
                if not products_data:
                    # No results from Ingram Micro, search Excel file
                    excel_results = self.excel_api.search_products(self.excel_data, query)
                    if not excel_results.empty:
                        response = self.excel_api.format_results(excel_results)
                        response += "\n\nThese results are from our internal database as no products were found in the Ingram Micro catalog."
                    else:
                        response = "No products found in either the Ingram Micro catalog or our internal database."
                else:
                    response = self.format_products_response(products_data)
                    response += "\n\nTo see only available products, type 'show available products'."
                user_state['last_products'] = products_data  # Save the products for later filtering
                await turn_context.send_activity(Activity(type="message", text=response))

            elif user_message == "show available products":
                if 'last_products' in user_state:
                    available_products = self.ingram_api.filter_available_products(user_state['last_products'])
                    if available_products:
                        response = self.format_products_response(available_products)
                        response += "\n\nShowing only available products from your last search."
                    else:
                        response = "No available products found from your last search."
                else:
                    response = "Please perform a product search first before asking for available products."
                
                await turn_context.send_activity(Activity(type="message", text=response))

            elif product_id_search:
                product_id = product_id_search.group(1)
                user_state['last_query'] = product_id  # Save the context
                await turn_context.send_activity("Fetching price and availability. This may take a moment...")
                try:
                    product_details = await self.ingram_api.fetch_price_and_availability(product_id)
                    formatted_response = self.ingram_api.format_product_details([product_details])
                    await turn_context.send_activity(Activity(type="message", text=formatted_response))
                except asyncio.TimeoutError:
                    await turn_context.send_activity("I'm sorry, but the request for price and availability timed out. This product might not be available or there might be an issue with the service. Please try again later or contact support if the problem persists.")
                except Exception as e:
                    await turn_context.send_activity(f"An error occurred while fetching price and availability: {str(e)}")
            else:
                response = await self.get_openai_response(user_message, user_state)
                additional_instruction = ("\n\n**--To search the Ingram Micro Database for related products, please start your query with 'search product details for'.**")
                response += additional_instruction
                await turn_context.send_activity(Activity(type="message", text=response))

        except Exception as e:
            print(f"Exception in on_message_activity: {str(e)}")
            traceback.print_exc()
            await turn_context.send_activity("An error occurred while processing your message.")
        finally:
            await self.conversation_state.save_changes(turn_context)

    async def get_openai_response(self, user_message, user_state):
        context = "\n".join([f"{key}: {value}" for key, value in user_state.items()])
        prompt = (
            f"You are an assistant helping employees provide relevant product information to employees who reply to customers questions. "
            f"When asked a question, provide correct, concise, relevant, and to-the-point answers. "
            f"In your answers please do not mention anything about your latest update."
            f"Here is the current context of the conversation:\n{context}\n"
            f"Example user message: '{user_message}'"
            f"Make sure to include the most up-to-date and accurate information, particularly for product releases and specifications."
        )

        try:
            response = await self.openai_api.ask_openai(prompt)
        except Exception as e:
            print(f"OpenAI API call failed: {str(e)}")
            response = "I'm sorry, I couldn't retrieve the information at this time."

        return response

    def format_products_response(self, products):
        if not products:
            return "No products found for the given query."

        formatted_products = []
        for product in products:
            description = product.get('description', 'No description available')
            category = product.get('category', 'No category')
            vendor_name = product.get('vendorName', 'No vendor name')
            sub_category = product.get('subCategory', 'No subcategory')
            product_type = product.get('productType', 'No product type')
            links_info = "No direct link available"
            if 'links' in product and product['links']:
                link = next((link for link in product['links'] if link.get('type') == 'GET'), None)
                if link:
                    links_info = link['href']
            formatted_product = (
                f"**Product Details:** {vendor_name} - {description}  \n"
                f"**Category:** {category} - {sub_category}  \n"
                f"**Product Type:** {product_type}  \n"
                f"**Price and availability information:** {links_info}"
            )
            formatted_products.append(formatted_product)
        additional_instruction = "\n\n**--If your results are not relevant, consider refining your search. \n\n**--To check price and availability for any of these products, please use 'price and availability for' followed by the product ID.**"
        formatted_products.append(additional_instruction)
        return "\n\n".join(formatted_products)