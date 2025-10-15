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
        self.client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        self.models = ["gemini-2.5-pro"] #, "gemini-2.5-flash", "gemini-2.5-flash-lite"]                  
                        
    def get_response(self, query):  
        if self.models:      
            try:            
                model = self.models[0]
                logger.info("Using Open GenAI model: %s", model)
                response = self.client.models.generate_content(
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
        else:
            logger.warning("No more GenAI AI models to try.")
            
        return None, None
    
