import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from botbuilder.core import TurnContext, Activity, ConversationState
from botbuilder.schema import Mention
from bots.echo_bot import CustomEchoBot
from api.openai_api import OpenAIAPI

class TestCustomEchoBot(unittest.TestCase):
    def test_on_message_activity_keyword_search(self):
        # Arrange
        conversation_state = ConversationState(None)
        ingram_api = MagicMock()
        openai_api = OpenAIAPI()
        bot = CustomEchoBot(conversation_state, ingram_api, openai_api)

        # Act
        turn_context = MagicMock(spec=TurnContext)
        turn_context.activity = Activity(text="search product details for laptop")
        bot.on_message_activity(turn_context)
        # Add assertions for the expected behavior

    def test_on_message_activity_product_id_search(self):
        # Arrange
        conversation_state = ConversationState(None)
        ingram_api = MagicMock()
        openai_api = OpenAIAPI()
        bot = CustomEchoBot(conversation_state, ingram_api, openai_api)

        # Act
        turn_context = MagicMock(spec=TurnContext)
        turn_context.activity = Activity(text="price and availability for ABC123")
        bot.on_message_activity(turn_context)
        # Add assertions for the expected behavior

    def test_on_message_activity_openai_api(self):
        # Arrange
        conversation_state = ConversationState(None)
        ingram_api = MagicMock()
        openai_api = MagicMock()
        bot = CustomEchoBot(conversation_state, ingram_api, openai_api)

        # Act
        turn_context = MagicMock(spec=TurnContext)
        user_message = "Hello, how are you?"
        turn_context.activity = Activity(text=user_message)

        openai_api.ask_openai = AsyncMock(return_value="I'm doing great, thanks for asking!")
        bot.on_message_activity(turn_context)

        # Assert
        openai_api.ask_openai.assert_called_once_with(user_message)
        turn_context.send_activity.assert_called_once_with(Activity(type="message", text="I'm doing great, thanks for asking!"))

    @patch('bots.echo_bot.CustomEchoBot.call_openai_api')
    def test_on_message_activity_openai_api_error(self, mock_call_openai_api):
        # Arrange
        conversation_state = ConversationState(None)
        ingram_api = MagicMock()
        openai_api = OpenAIAPI()
        bot = CustomEchoBot(conversation_state, ingram_api, openai_api)

        # Act
        turn_context = MagicMock(spec=TurnContext)
        user_message = "Hello, how are you?"
        turn_context.activity = Activity(text=user_message)

        mock_call_openai_api.side_effect = Exception("OpenAI API error")
        bot.on_message_activity(turn_context)

        # Assert
        mock_call_openai_api.assert_called_once_with(user_message)
        turn_context.send_activity.assert_called_once_with(Activity(type="message", text="Failed to get response from OpenAI API: OpenAI API error"))

    def test_call_openai_api(self):
        # Arrange
        conversation_state = ConversationState(None)
        ingram_api = MagicMock()
        openai_api = OpenAIAPI()
        bot = CustomEchoBot(conversation_state, ingram_api, openai_api)

        # Act
        user_message = "Hello, how are you?"
        openai_api.ask_openai = AsyncMock(return_value="I'm doing great, thanks for asking!")
        response = bot.call_openai_api(user_message)

        # Assert
        self.assertEqual(response, "I'm doing great, thanks for asking!")
