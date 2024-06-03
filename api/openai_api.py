import openai
import aiohttp
from dotenv import load_dotenv
from config import DefaultConfig

load_dotenv()

CONFIG = DefaultConfig()

class OpenAIAPI:
    def __init__(self):
        self.api_key = CONFIG.OPENAI_API_KEY

    async def ask_openai(self, prompt):
        openai.api_key = self.api_key  # Set the OpenAI API key
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "gpt-4-turbo",
            "messages": [{"role": "user", "content": prompt}]
        }
        url = "https://api.openai.com/v1/chat/completions"

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['choices'][0]['message']['content'].strip()
                else:
                    print("Failed to process request with OpenAI:", response.status, await response.text())
                    return "I had an error processing your request. Please try again later."
