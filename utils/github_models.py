import logging
import os
from dotenv import load_dotenv
from openai import OpenAI

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GithubModels():
    def __init__(self):     
        load_dotenv()  
        self.endpoint = "https://models.github.ai/inference"
        
        self.clients = [
            OpenAI(
                api_key = os.getenv("GITHUB_TOKEN"),
                base_url = self.endpoint,
            ),
            OpenAI(
                api_key = os.getenv("GITHUB_TOKEN_2"),
                base_url = self.endpoint,
            )
        ]
            
        
        # self.models = ["xai/grok-3-mini", "xai/grok-3", "openai/gpt-4.1-nano", "openai/gpt-4.1-mini", "openai/gpt-4.1"] #, "openai/gpt-4o-mini", "openai/gpt-4o"]
        #self.models = ["xai/grok-3", "openai/gpt-4.1"]
         #, 'openai/gpt-4.1']
        #, 'openai/gpt-5', 'openai/gpt-5', 'openai/gpt-5-mini']
        
        self.models = ['openai/gpt-4.1', 'openai/gpt-4.1-mini', 'xai/grok-3']
        #self.models = ['openai/gpt-4.1', 'openai/gpt-4.1-mini']

        
    def get_response(self, query):  
        if self.models:      
            try:   
                client = self.clients[0]         
                model = self.models[0]
                logger.info("Using Open AI model: %s", model)
                response = client.chat.completions.create(
                    model = model,
                    messages=[
                        {"role": "user", "content": query}                
                    ],
                )
                content = response.choices[0].message.content
                logger.info(content)
                return content, model
            except Exception as e:
                logger.error("Error in GithubModels.get_response: %s", e)
                
                if len(self.clients) > 1:
                    self.clients.remove(client)
                else:                        
                    self.models.remove(model)
                        
                self.models.remove(model)
                if self.models:                
                    return self.get_response(query)
                else:
                    logger.warning("No more Open AI models to try.")
        else:
            logger.warning("No more Open AI models to try.")
            
        return None, None
