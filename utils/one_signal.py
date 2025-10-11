
from datetime import datetime
import json
import os
import uuid
import requests
from dotenv import load_dotenv

class OneSignal():
    def __init__(self):
        load_dotenv()        
        self.base_url = "https://api.onesignal.com"
        self.headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Key {os.getenv('ONE_SIGNAL_API_KEY')}"
        }     
         
    def send_push_notification(self, message):
        print(f'sending push notification... {message}')
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
                "big_picture": "https://i.postimg.cc/9MmQpMRr/cropped-circle-image-1.png",
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
            print(response.json())
            return response.json()
            
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"An error occurred: {req_err}")
        except Exception as err:
            print(f"Unexpected error: {err}")
    
    def __call__(self):
        self.send_push_notification("New Predictions have Just been Posted! Open App & Refresh to see them (Pull to Refresh)!!!")

