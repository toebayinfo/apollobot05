import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file if present

class DefaultConfig:
    PORT = int(os.environ.get("PORT", 8000))
    MICROSOFT_APP_ID = os.environ.get("MicrosoftAppId", "")
    MICROSOFT_APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
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
        print(f"AZURE_CLIENT_ID: {self.AZURE_CLIENT_ID}")
        print(f"AZURE_CLIENT_SECRET: {self.AZURE_CLIENT_SECRET[:5]}...")  # Print only first 5 chars for security
        print(f"AZURE_TENANT_ID: {self.AZURE_TENANT_ID}")
        print(f"SHAREPOINT_SITE_URL: {self.SHAREPOINT_SITE_URL}")
        print(f"EXCEL_FILE_URL: {self.EXCEL_FILE_URL}")

CONFIG = DefaultConfig()

