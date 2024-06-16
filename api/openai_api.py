import os
from openai import AsyncOpenAI
from config import CONFIG
from aiohttp import ClientSession, TCPConnector

class OpenAIAPI:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=CONFIG.OPENAI_API_KEY)
        self.session = ClientSession(connector=TCPConnector(limit=10))  # Adjust the limit as needed

    async def ask_openai(self, prompt):
        # Optimize the prompt to be concise
        optimized_prompt = self.optimize_prompt(prompt)

        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": optimized_prompt}]
        }

        try:
            response = await self.client.chat.completions.create(**payload)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return "An unexpected error occurred. Please try again."

    def optimize_prompt(self, prompt):
        # Add logic to optimize the prompt here
        return prompt.strip()

    async def close(self):
        await self.client.aclose()
        await self.session.close()