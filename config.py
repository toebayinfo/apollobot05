import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file if present

class DefaultConfig:
    # API key for OpenAI services
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "default_openai_api_key")

    # Ingram Micro API credentials
    INGRAM_CLIENT_ID = os.getenv("INGRAM_CLIENT_ID", "default_client_id")
    INGRAM_CLIENT_SECRET = os.getenv("INGRAM_CLIENT_SECRET", "default_client_secret")
    INGRAM_CUSTOMER_NUMBER = os.getenv("INGRAM_CUSTOMER_NUMBER", "default_customer_number")

# Create an instance of the DefaultConfig class and export it
CONFIG = DefaultConfig()
