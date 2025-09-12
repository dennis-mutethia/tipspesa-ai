import os
from dotenv import load_dotenv
from openai import OpenAI

class Grok():
    def __init__(self):     
        load_dotenv()  
        self.endpoint = "https://models.github.ai/inference"
        
        self.client = OpenAI(
            api_key = os.getenv("GITHUB_TOKEN"),
            base_url = self.endpoint,
        )
        
        self.models = ["xai/grok-3-mini", "xai/grok-3", "openai/gpt-5-nano", "openai/gpt-5-mini", "openai/gpt-5", "openai/gpt-4.1-nano", "openai/gpt-4.1-mini", "openai/gpt-4.1"]
        #self.models = ["openai/gpt-5-mini"]
        #"deepseek/DeepSeek-R1-0528"]
        
    def get_response(self, query):
        model = self.models[0]
        try:
            print(f"Using model: {model}")
            response = self.client.chat.completions.create(
                model = model,
                messages=[
                    {"role": "user", "content": query}                
                ],
            )
            content = response.choices[0].message.content
            print(content)
            return content
        except Exception as e:
            print(f"Error in Grok.get_response: {e}")
            if "RateLimitReached" in str(e):
                self.models.remove(model)
                if self.models:                
                    return self.get_response(query)
                else:
                    print("No more models to try.")
            return None