

import os
from dotenv import load_dotenv
import logging

from flask import Flask, jsonify

from tasks import predict, results, withdraw_and_autobet

# Load environment variables from .env file
load_dotenv()

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

        
# Routes
@app.route('/')
def index():    
    return 'Running...'

@app.route('/cron/predict')
def predict_job():
    try:
        predict()  # Your existing scheduler function
        logger.info("Predict job completed successfully")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error("Predict job failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/cron/results')
def results_job():
    try:
        results()  # Your existing scheduler function
        logger.info("Results job completed successfully")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error("Results job failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/cron/withdraw-autobet')
def withdraw_and_autobet_job():
    try:
        withdraw_and_autobet()  # Your existing scheduler function
        logger.info("Withdraw & Autobet job completed successfully")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error("Withdraw & Autobet job failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    debug_mode = os.getenv('IS_DEBUG', 'False') in ['True', '1', 't']
        
    # Run the Flask app
    app.run(debug=debug_mode)