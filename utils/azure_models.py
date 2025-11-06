import logging
import os
from dotenv import load_dotenv
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

logger = logging.getLogger(__name__)

class AzureModels():
    def __init__(self):     
        load_dotenv()  
        endpoint = "https://models.github.ai/inference"
        api_keys = os.getenv("GITHUB_TOKENS").split(",")
        
        self.clients = [
            ChatCompletionsClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(api_key.strip())
            ) for api_key in api_keys
        ]
                
        self.models = os.getenv("AZURE_MODELS").split(",")
            
        
    def get_response(self, query):  
        if self.clients:
            client = self.clients[0] 
            if self.models:      
                try:    
                    model = self.models[0]
                    logger.info("Using Azure model: %s", model)
                    response = client.complete(
                        messages=[
                            #SystemMessage("You are a helpful assistant."),
                            UserMessage(query)
                        ],
                        model=model
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
                        logger.warning("No more Azure models to try.")
                        self.clients.remove(client)
                        self.models = os.getenv("AZURE_MODELS").split(",")
                        if self.clients:
                            return self.get_response(query)
                        else:
                            logger.warning("No more GitHub accounts to try.")
            else:
                logger.warning("No more Azure models to try.")
        else:
            logger.warning("No more GitHub accounts to try.")
                
        return None, None
