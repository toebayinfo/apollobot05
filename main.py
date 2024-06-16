import os
import logging
import json
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.integration.aiohttp import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity
from botbuilder.core import ConversationState, MemoryStorage
from config import CONFIG
from bots.echo_bot import CustomEchoBot
from http import HTTPStatus
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create adapter settings
adapter_settings = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(adapter_settings)

# Create conversation state with MemoryStorage
memory_storage = MemoryStorage()
conversation_state = ConversationState(memory_storage)

# Create the Bot
BOT = CustomEchoBot(conversation_state)

# Listen for incoming requests on /api/messages
async def messages(req: Request) -> Response:
    if req.method == 'POST':
        if req.content_type == "application/json":
            try:
                body = await req.json()
                logger.info(f"Received request body: {json.dumps(body, indent=2)}")
            except Exception as e:
                logger.error(f"Error parsing request body: {e}")
                return Response(status=HTTPStatus.BAD_REQUEST, text=f"Error parsing request body: {e}")
        else:
            logger.error("Unsupported Media Type")
            return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

        try:
            activity = Activity().deserialize(body)
            logger.info(f"Deserialized activity: {activity}")
        except Exception as e:
            logger.error(f"Failed to deserialize activity: {e}")
            return Response(status=HTTPStatus.BAD_REQUEST, text=f"Failed to deserialize activity: {e}")

        auth_header = req.headers.get("Authorization", "")

        try:
            response = await ADAPTER.process_activity(auth_header, activity, BOT.on_turn)
            if response:
                return json_response(data=response.body, status=response.status)
            return Response(status=HTTPStatus.OK)
        except Exception as e:
            logger.error(f"Error processing activity: {e}")
            return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR, text=str(e))
    else:
        return Response(status=HTTPStatus.METHOD_NOT_ALLOWED)

# Health check endpoint
async def health_check(req: Request) -> Response:
    return Response(status=HTTPStatus.OK)

def init_func(argv):
    app = web.Application(middlewares=[aiohttp_error_middleware])
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health_check)
    return app

if __name__ == "__main__":
    APP = init_func(None)
    try:
        port = int(os.environ.get("PORT", 8000))
        web.run_app(APP, host="0.0.0.0", port=port)
    except Exception as error:
        logger.error(f"Failed to start the app: {error}")
        raise error
