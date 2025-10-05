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
        
        #self.models = ["xai/grok-3-mini", "xai/grok-3", "openai/gpt-4.1-nano", "openai/gpt-4.1-mini", "openai/gpt-4.1"] #, "openai/gpt-4o-mini", "openai/gpt-4o"]
        #self.models = ["xai/grok-3", "openai/gpt-4.1"]
        self.models = ["xai/grok-3", "xai/grok-3-mini", "openai/gpt-5", "openai/gpt-5", "openai/gpt-5-mini"]
        
    def get_response(self, query):  
        if self.models:      
            try:            
                model = self.models[0]
                print(f"Using Open AI model: {model}")
                response = self.client.chat.completions.create(
                    model = model,
                    messages=[
                        {"role": "user", "content": query}                
                    ],
                )
                content = response.choices[0].message.content
                print(content)
                return content, model
            except Exception as e:
                print(f"Error in Grok.get_response: {e}")
                if "RateLimitReached" in str(e):
                    self.models.remove(model)
                    if self.models:                
                        return self.get_response(query)
                    else:
                        print("No more Open AI models to try.")
        else:
            print("No more Open AI models to try.")
            
        return None, None