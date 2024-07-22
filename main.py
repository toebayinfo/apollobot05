import os
import json
import logging
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from aiohttp_cors import setup as setup_cors, ResourceOptions
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from botbuilder.schema import Activity
from botbuilder.core import ConversationState, MemoryStorage
from config import CONFIG
from bots.echo_bot import CustomEchoBot
from http import HTTPStatus

# Set up logging
logging.basicConfig(level=CONFIG.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create authentication and adapter
auth = ConfigurationBotFrameworkAuthentication(CONFIG)
ADAPTER = CloudAdapter(auth)

# Create conversation state with MemoryStorage
memory_storage = MemoryStorage()
conversation_state = ConversationState(memory_storage)

# Create the Bot
BOT = CustomEchoBot(conversation_state)

# Listen for incoming requests on /api/messages
async def messages(req: Request) -> Response:
    logger.debug(f"Received request headers: {req.headers}")
    logger.debug(f"Received request method: {req.method}")

    if req.method == 'POST':
        if "application/json" in req.headers.get("Content-Type", ""):
            try:
                body = await req.json()
                logger.debug(f"Received request body: {json.dumps(body, indent=2)}")
            except Exception as e:
                logger.error(f"Error parsing request body: {e}")
                return Response(status=HTTPStatus.BAD_REQUEST, text=f"Error parsing request body: {e}")
        else:
            logger.error("Unsupported Media Type")
            return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

        try:
            activity = Activity().deserialize(body)
            logger.debug(f"Deserialized activity: {activity}")
        except Exception as e:
            logger.error(f"Failed to deserialize activity: {e}")
            return Response(status=HTTPStatus.BAD_REQUEST, text=f"Failed to deserialize activity: {e}")

        auth_header = req.headers.get("Authorization", "")
        try:
            logger.debug(f"Processing activity with auth header: {auth_header[:10]}...")  # Log first 10 chars of auth header
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
    return Response(text="Healthy", status=HTTPStatus.OK)

# Root path handler
async def root(req: Request) -> Response:
    return Response(text="Bot is running!", status=HTTPStatus.OK)

def init_func(argv):
    app = web.Application(middlewares=[aiohttp_error_middleware])
    
    # Setup CORS
    cors = setup_cors(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health_check)
    app.router.add_get("/", root)

    # Configure CORS on all routes
    for route in list(app.router.routes()):
        cors.add(route)

    return app

if __name__ == "__main__":
    APP = init_func(None)
    try:
        web.run_app(APP, host="0.0.0.0", port=CONFIG.PORT)
    except Exception as error:
        logger.error(f"Failed to start the app: {error}")
        raise error