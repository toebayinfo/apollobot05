import asyncio
import re
import traceback
from botbuilder.core import ActivityHandler, TurnContext, ConversationState
from botbuilder.schema import Activity
from api.ingram_api import IngramAPI
from api.openai_api import OpenAIAPI

class CustomEchoBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState):
        self.ingram_api = IngramAPI()
        self.openai_api = OpenAIAPI()
        self.conversation_state = conversation_state
        self.user_state_accessor = self.conversation_state.create_property("UserState")
        self.welcomed_user_ids = set()

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
        
            await self.ingram_api.ensure_access_token()
            user_message = turn_context.activity.text.lower()
        
            keyword_search = re.search(r"search product details for (.+)", user_message)
            product_id_search = re.search(r"price and availability for (\w+)", user_message)

            if keyword_search:
                query = keyword_search.group(1)
                user_state['last_query'] = query  # Save the context
                
                products_data = await self.ingram_api.fetch_products(query)
                response = self.format_products_response(products_data)
                response_activity = Activity(type="message", text=response)
                await turn_context.send_activity(response_activity)
            elif product_id_search:
                product_id = product_id_search.group(1)
                user_state['last_query'] = product_id  # Save the context
                await turn_context.send_activity("Fetching price and availability. This may take a moment...")
                try:
                    response = await self.ingram_api.fetch_price_and_availability(product_id)
                    formatted_response = self.ingram_api.format_product_details(response)
                    await turn_context.send_activity(Activity(type="message", text=formatted_response))
                except asyncio.TimeoutError:
                    await turn_context.send_activity("I'm sorry, but the request for price and availability timed out. This product might not be available or there might be an issue with the service. Please try again later or contact support if the problem persists.")
                except Exception as e:
                    await turn_context.send_activity(f"An error occurred while fetching price and availability: {str(e)}")
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
        conversation_id = turn_context.activity.conversation.id

        for member in members_added:
            if member.id != turn_context.activity.recipient.id and member.id not in self.welcomed_user_ids:
                self.welcomed_user_ids.add(member.id)
                welcome_text = "Welcome to the Apollo Bot! How can I help you today?"
                await turn_context.send_activity(Activity(type="message", text=welcome_text))

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
        additional_instruction = "\n\n**--To check price and availability for any of these products, please use 'price and availability for' followed by the product ID.**"
        formatted_products.append(additional_instruction)
        return "\n\n".join(formatted_products)