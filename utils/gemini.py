import os
from dotenv import load_dotenv
from google import genai

class Gemini():
    def __init__(self):        
        load_dotenv()
        self.client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = "gemini-2.5-flash"
        
    def get_response(self, query):
        while True:
            try:
                print(f"Using Open GenAI model: {self.model}")
                response = self.client.models.generate_content(
                    model= self.model,
                    contents=str(query)
                )
                content = response.text
                print(content)
                return content, self.model
            
            except Exception as e:
                print(f"Error in Gemini.get_response: {e}")
                if "overloaded" in str(e):
                    return self.get_response(query)
                return None, self.model
    