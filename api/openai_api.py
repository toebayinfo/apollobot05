import openai
import aiohttp
from config import CONFIG

class OpenAIAPI:
    def __init__(self):
        self.api_key = CONFIG.OPENAI_API_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.url = "https://api.openai.com/v1/chat/completions"
        self.session = aiohttp.ClientSession(headers=self.headers)

    async def ask_openai(self, prompt):
        openai.api_key = self.api_key  # Set the OpenAI API key globally if needed
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            async with self.session.post(self.url, json=payload) as response:
                response.raise_for_status()  # Will raise an HTTPError for bad responses
                data = await response.json()
                return data['choices'][0]['message']['content'].strip()
        except aiohttp.ClientResponseError as e:
            print("Failed to process request with OpenAI:", e.status, await e.message())
            return "I had an error processing your request. Please try again later."
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return "An unexpected error occurred. Please try again."

    async def close(self):
        await self.session.close()
