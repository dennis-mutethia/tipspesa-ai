
from datetime import datetime
import json
import logging
import os
import requests
from dotenv import load_dotenv


# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OneSignal():
    def __init__(self):
        load_dotenv()        
        self.base_url = "https://api.onesignal.com"
        self.headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Key {os.getenv('ONE_SIGNAL_API_KEY')}"
        }     
         
    def send_push_notification(self, message):
        logger.info('sending push notification... %s', message)
        try:
            url = f"{self.base_url}/notifications"
            payload ={
                "app_id": os.getenv('ONE_SIGNAL_APP_ID'),
                "target_channel": "push",
                "name": f"Predictions - {datetime.now()}",
                "headings": {
                    "en": "🔥 New Predictions Just Dropped! 🔥"
                },
                "contents": {
                    "en": message
                },
                "big_picture": "https://tipspesa.vercel.app/static/puh-notification-image.JPG",
                "included_segments": [
                    "Active Subscriptions", #Session within the last 7 days
                    "Engaged Subscriptions", #4+ Sessions within the last 7 days
                    "Inactive Subscriptions", #No Session within the last 7 days
                    "Total Subscriptions"
                ],
            }
            # Sending the POST request
            response = requests.post(
                url,                 
                headers=self.headers,
                data=json.dumps(payload)
            )
            logger.info(response.json())
            return response.json()
        
        except requests.exceptions.HTTPError as http_err:
            logger.error("HTTP error occurred: %s", http_err)
        except requests.exceptions.ConnectionError as conn_err:
            logger.error("Connection error occurred: %s", conn_err)
        except requests.exceptions.Timeout as timeout_err:
            logger.error("Timeout error occurred: %s", timeout_err)
        except requests.exceptions.RequestException as req_err:
            logger.error("An error occurred: %s", req_err)
        except Exception as err:
            logger.error("Unexpected error: %s", err)
    
    def __call__(self):
        self.send_push_notification("New Predictions have Just been Posted! Open App & Refresh to see them (Pull to Refresh)!!!")

            
if __name__ == "__main__":
    try: 
        OneSignal()()
    except Exception as e:
        logger.error(e)
        