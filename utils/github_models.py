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
        api_keys = os.getenv("GITHUB_TOKEN").split(",")
        
        self.clients = [
            OpenAI(
                api_key = api_key.strip(),
                base_url = self.endpoint,
            ) for api_key in api_keys
        ]
            
        
        # self.models = ["xai/grok-3-mini", "xai/grok-3", "openai/gpt-4.1-nano", "openai/gpt-4.1-mini", "openai/gpt-4.1"] #, "openai/gpt-4o-mini", "openai/gpt-4o"]
        #self.models = ["xai/grok-3", "openai/gpt-4.1"]
         #, 'openai/gpt-4.1']
        #, 'openai/gpt-5', 'openai/gpt-5', 'openai/gpt-5-mini']
        
        self.models = ['openai/gpt-4.1', 'openai/gpt-4.1-mini', 'xai/grok-3']
        #self.models = ['openai/gpt-4.1', 'openai/gpt-4.1-mini']

        
    def get_response(self, query):  
        if self.clients:
            client = self.clients[0] 
            if self.models:      
                try:    
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
                    
                    self.models.remove(model)        
                    if self.models:                
                        return self.get_response(query)                    
                    else:
                        logger.warning("No more Open AI models to try.")
                        self.clients.remove(client)
                        if self.clients:
                            return self.get_response(query)
                        else:
                            logger.warning("No more Open AI accounts to try.")
            else:
                logger.warning("No more Open AI models to try.")
        else:
            logger.warning("No more Open AI accounts to try.")
                
        return None, None
