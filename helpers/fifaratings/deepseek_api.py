import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional

class DeepSeekAPI:
    def __init__(self, base_url: str = "https://api.deepseek.com"):
        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.default_model = "deepseek-chat"
        self.default_system_message = "You are a helpful assistant"

    def create_chat_completion(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> str:
        messages = [
            {"role": "system", "content": system_message or self.default_system_message},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            stream=stream,
            **kwargs
        )
        
        if stream:
            return self._handle_streaming_response(response)
        return response.choices[0].message.content

    def _handle_streaming_response(self, response):
        collected_chunks = []
        for chunk in response:
            if chunk.choices[0].delta.content:
                collected_chunks.append(chunk.choices[0].delta.content)
        return "".join(collected_chunks)

# Usage example
if __name__ == "__main__":
    ds = DeepSeekAPI()
    response = ds.create_chat_completion("Hello, how are you?")
    print(response)