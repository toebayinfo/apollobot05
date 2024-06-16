import re
import traceback
import json
from botbuilder.core import ActivityHandler, TurnContext, ConversationState
from botbuilder.schema import Activity
from api.ingram_api import IngramAPI
from api.openai_api import OpenAIAPI
from main import get_cached_data, set_cache_data  # Import cache functions from main

class CustomEchoBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState):
        self.ingram_api = IngramAPI()
        self.openai_api = OpenAIAPI()
        self.conversation_state = conversation_state
        self.user_state_accessor = self.conversation_state.create_property("UserState")

    async def on_turn(self, turn_context: TurnContext):
        try:
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
            user_message = turn_context.activity.text.lower()
        
            keyword_search = re.search(r"search product details for (.+)", user_message)
            product_id_search = re.search(r"price and availability for (\w+)", user_message)

            if keyword_search:
                query = keyword_search.group(1)
                user_state['last_query'] = query  # Save the context
                preprocessed_query = self.preprocess_query(query)
            
                # Check cache first
                cache_key = f"product_search_{preprocessed_query}"
                products_data = get_cached_data(cache_key)
                if not products_data:
                    products_data = await self.ingram_api.fetch_products(preprocessed_query)
                    set_cache_data(cache_key, products_data)
                
                response = self.format_products_response(products_data)
                response_activity = Activity(type="message", text=response)
                await turn_context.send_activity(response_activity)
            elif product_id_search:
                product_id = product_id_search.group(1)
                user_state['last_query'] = product_id  # Save the context
                
                # Check cache first
                cache_key = f"product_price_{product_id}"
                response = get_cached_data(cache_key)
                if not response:
                    response = await self.ingram_api.fetch_price_and_availability(product_id)
                    set_cache_data(cache_key, response)
                    
                await turn_context.send_activity(Activity(type="message", text=response))
            else:
                response = await self.get_openai_response(user_message, user_state)
                additional_instruction = ("  \n\n**--To search the Ingram Micro Database for related products, please start your query with 'search product details for'.**")
                response += additional_instruction
                response_activity = Activity(type="message", text=response)
                await turn_context.send_activity(response_activity)
        except Exception as e:
            print(f"Exception in on_message_activity: {str(e)}")
            traceback.print_exc()
            await turn_context.send_activity("An error occurred while processing your message.")
        finally:
            await self.conversation_state.save_changes(turn_context)

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                welcome_text = "Welcome to the Apollo Bot! How can I help you today?"
                await turn_context.send_activity(Activity(type="message", text=welcome_text))

    def preprocess_query(self, query):
        return query.lower().replace("laptop", "notebook")

    async def get_openai_response(self, user_message, user_state):
        context = "\n".join([f"{key}: {value}" for key, value in user_state.items()])
        prompt = (
            f"You are an assistant helping employees provide relevant product information to employees who reply to customers questions. "
            f"When asked a question, provide correct, concise, relevant, and to-the-point answers. "
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
                link = next((link for link in product['links'] if link.get('type') == 'productDetail'), None)
                if link:
                    links_info = f"[Click here to view]({link.get('url')})"
            formatted_product = (
                f"**Description:** {description}\n"
                f"**Category:** {category}\n"
                f"**Sub-Category:** {sub_category}\n"
                f"**Vendor Name:** {vendor_name}\n"
                f"**Product Type:** {product_type}\n"
                f"**Links:** {links_info}\n"
            )
            formatted_products.append(formatted_product)

        return "\n\n".join(formatted_products)
