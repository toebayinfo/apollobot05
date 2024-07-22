import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Set up logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

class DefaultConfig:
    PORT = int(os.environ.get("PORT", 8000))
    APP_ID = os.environ.get("MicrosoftAppId", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
    INGRAM_CLIENT_ID = os.environ.get("INGRAM_CLIENT_ID", "")
    INGRAM_CLIENT_SECRET = os.environ.get("INGRAM_CLIENT_SECRET", "")
    INGRAM_CUSTOMER_NUMBER = os.environ.get("INGRAM_CUSTOMER_NUMBER", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
    AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
    AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
    SHAREPOINT_SITE_URL = os.environ.get("SHAREPOINT_SITE_URL", "")
    EXCEL_FILE_URL = os.environ.get("EXCEL_FILE_URL", "")

    def __init__(self):
        # Log configuration details at DEBUG level
        logger.debug(f"APP_ID: {self.APP_ID}")
        logger.debug(f"APP_PASSWORD: {'Set' if self.APP_PASSWORD else 'Not set'}")
        logger.debug(f"AZURE_CLIENT_ID: {self.AZURE_CLIENT_ID}")
        logger.debug(f"AZURE_CLIENT_SECRET: {'Set' if self.AZURE_CLIENT_SECRET else 'Not set'}")
        logger.debug(f"AZURE_TENANT_ID: {self.AZURE_TENANT_ID}")
        logger.debug(f"SHAREPOINT_SITE_URL: {self.SHAREPOINT_SITE_URL}")
        logger.debug(f"EXCEL_FILE_URL: {self.EXCEL_FILE_URL}")

# Create a single instance of DefaultConfig
CONFIG = DefaultConfig()