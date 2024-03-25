import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler

# Load data from CSV
def load_data(file_path):
    df = pd.read_csv(file_path, delimiter='\t', parse_dates={'datetime': ['<DATE>', '<TIME>']})
    return df

# Normalize data between 0 and 1
def normalize_data(data):
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data.reshape(-1, 1))
    return scaled_data, scaler

# Prepare data for training
def prepare_data(data, seq_length):
    X, Y = [], []
    for i in range(len(data) - seq_length - 1):
        window = data[i:(i + seq_length)]
        X.append(window)
        Y.append(data[i + seq_length])
    return np.array(X), np.array(Y)

# Define the model
def create_model(seq_length):
    model = tf.keras.models.Sequential([
        tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(seq_length, 1)),
        tf.keras.layers.LSTM(50),
        tf.keras.layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model

# Main function to train and evaluate the model
def main():
    # Hyperparameters
    seq_length = 10  # Length of input sequence
    epochs = 100
    batch_size = 32
    file_path = 'EURUSD_data.csv'

    # Load and preprocess data
    df = load_data(file_path)
    data = df['<CLOSE>'].values  # Assuming 'CLOSE' column contains the closing prices
    scaled_data, scaler = normalize_data(data)
    X, Y = prepare_data(scaled_data, seq_length)

    # Reshape data for LSTM input (samples, timesteps, features)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))

    # Split data into train and test sets
    split_ratio = 0.8
    split_index = int(split_ratio * len(X))
    X_train, X_test = X[:split_index], X[split_index:]
    Y_train, Y_test = Y[:split_index], Y[split_index:]

    # Create the model
    model = create_model(seq_length)

    # Train the model
    model.fit(X_train, Y_train, epochs=epochs, batch_size=batch_size, verbose=1)

    # Evaluate the model
    train_loss = model.evaluate(X_train, Y_train, verbose=0)
    test_loss = model.evaluate(X_test, Y_test, verbose=0)
    print(f'Training Loss: {train_loss}')
    print(f'Test Loss: {test_loss}')

    # Save the model for later use in MetaTrader
    model.save('stock_prediction_model.h5')
    print("Model saved successfully.")

if __name__ == "__main__":
    main()
