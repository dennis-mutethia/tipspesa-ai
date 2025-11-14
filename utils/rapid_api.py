
import requests
import os
from dotenv import load_dotenv

load_dotenv() 

class RapidAPI():
    def __init__(self):
        self.base_url = "https://free-api-live-football-data.p.rapidapi.com"
        self.headers = {
            'x-rapidapi-key': os.getenv("RAPIDAPI_KEY"),
            'x-rapidapi-host': "free-api-live-football-data.p.rapidapi.com"
        }
        
    def get_data(self, endpoint, params=None):        
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()  # Raise an error for bad responses
            return response.json().get("response", {})
        
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
    
    
    def get_events_by_date(self, date):
        endpoint = f"/football-get-matches-by-date"
        params = {"date": date}
        return self.get_data(endpoint, params)        
            
if __name__ == "__main__":
    api = RapidAPI()
    # data = api.get_data("/football-players-search", params={"search": "m"})
    # print(data).
    events = api.get_events_by_date("20251115")
    for match in events.get("matches", []):
        print(
            match.get("time"),
            match.get("home").get("name"), "vs", match.get("away").get("name")
        )