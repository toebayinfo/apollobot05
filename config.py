import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file if present

class DefaultConfig:
    """ Bot Configuration """

    PORT = 8000
    APP_ID = os.getenv("MicrosoftAppId", "default_app_id")
    APP_PASSWORD = os.getenv("MicrosoftAppPassword", "default_app_password")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "default_openai_api_key")
    INGRAM_CLIENT_ID = os.getenv("INGRAM_CLIENT_ID", "default_client_id")
    INGRAM_CLIENT_SECRET = os.getenv("INGRAM_CLIENT_SECRET", "default_client_secret")
    INGRAM_CUSTOMER_NUMBER = os.getenv("INGRAM_CUSTOMER_NUMBER", "default_customer_number")

CONFIG = DefaultConfig()
