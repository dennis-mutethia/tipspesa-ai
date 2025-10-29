

import atexit
import os
from dotenv import load_dotenv
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

from tasks import predict, results, withdraw_and_autobet

# Load environment variables from .env file
load_dotenv()

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Start the scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=predict, trigger="interval", hours=1)
scheduler.add_job(func=results, trigger="interval", minutes=5)
scheduler.add_job(func=withdraw_and_autobet, trigger="interval", minutes=4)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

        
# Routes
@app.route('/')
def index():    
    return 'Running...'


if __name__ == '__main__':
    debug_mode = os.getenv('IS_DEBUG', 'False') in ['True', '1', 't']
        
    # Run the Flask app
    app.run(debug=debug_mode)