# predict.py
import sys
import pandas as pd
from keras.models import load_model

# Load the Keras model
model = load_model('stock_prediction_model.h5')

# Load the market data from CSV
market_data = pd.read_csv(sys.argv[1])

# Make predictions
predictions = model.predict(market_data)

# Save predictions to CSV
pd.DataFrame(predictions).to_csv(sys.argv[2], index=False)