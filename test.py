

import logging
from tasks.autobet import Autobet
from tasks.predict import Predict
from tasks.predict_jackpot import PredictJackpot


# Global logging configuration (applies to all modules)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'  # Optional: Custom date format (e.g., 2025-11-04 22:13:45)
)

Autobet()()