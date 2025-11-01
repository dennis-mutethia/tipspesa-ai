import logging
import os
from dotenv import load_dotenv
from google import genai

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Gemini():
    def __init__(self):        
        load_dotenv()
        api_keys = os.getenv("GITHUB_TOKEN").split(",")
        self.clients = [
            genai.Client(
                api_key=api_key.strip()
            ) for api_key in api_keys
        ]
        self.models = ["gemini-2.5-pro"] #, "gemini-2.5-flash", "gemini-2.5-flash-lite"]                  
                        
    def get_response(self, query):  
        if self.clients:
            client = self.clients[0] 
            if self.models:      
                try:
                    model = self.models[0]
                    logger.info("Using Open GenAI model: %s", model)
                    response = client.models.generate_content(
                        model= model,
                        contents=str(query)
                    )
                    content = response.text
                    logger.info(content)
                    return content, model
                except Exception as e:
                    logger.error("Error in Gemini.get_response: %s", e)
                    if "overloaded" in str(e):
                        return self.get_response(query)
                    elif "RESOURCE_EXHAUSTED" in str(e):
                        self.models.remove(model)                            
                        if self.models:                
                            return self.get_response(query)
                        else:
                            logger.warning("No more GenAI models to try.")
                            if self.clients:
                                self.clients.remove(client)
                                self.models = ["gemini-2.5-pro"]
                                if self.clients:                
                                    return self.get_response(query)
                                else:
                                    logger.warning("No more GenAI acounts to try.")
            else:
                logger.warning("No more GenAI AI models to try.")        
        else:
            logger.warning("No more GenAI acounts to try.")
                
        return None, None
    
