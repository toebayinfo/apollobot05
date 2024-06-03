import os
from dotenv import load_dotenv

load_dotenv()

class DefaultConfig:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    INGRAM_CLIENT_ID = os.getenv("INGRAM_CLIENT_ID")
    INGRAM_CLIENT_SECRET = os.getenv("INGRAM_CLIENT_SECRET")
    INGRAM_CUSTOMER_NUMBER = os.getenv("INGRAM_CUSTOMER_NUMBER")

# Create an instance of the DefaultConfig class and export it
CONFIG = DefaultConfig()