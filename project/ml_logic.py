import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
# KNN related import is removed
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
import json
from datetime import datetime, timedelta, date
import traceback # Keep for debugging if needed

# --- KNN removed from MODELS ---
MODELS = {
    'Linear Regression': LinearRegression(),
    'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42),
    # 'KNN' entry removed
    'XGBoost': XGBRegressor(n_estimators=100, random_state=42, objective='reg:squarederror')
}
# --- End of change ---

STOCK_TICKERS = {
    'TCS': 'TCS.NS',
    'HDFC': 'HDFCBANK.NS',
    'Infosys': 'INFY.NS',
    'Yes Bank': 'YESBANK.NS',
    'ITC': 'ITC.NS',
    'Adani Power': 'ADANIPOWER.NS'
}

def get_model(model_name):
    """Fetches an untrained model instance."""
    if model_name in MODELS:
        if model_name == 'Linear Regression': return LinearRegression()
        if model_name == 'Random Forest': return RandomForestRegressor(n_estimators=100, random_state=42)
        # KNN case removed
        if model_name == 'XGBoost': return XGBRegressor(n_estimators=100, random_state=42, objective='reg:squarederror')
    else:
        raise ValueError("Invalid model name provided.")

def fetch_historical_data(stock_name, years=2):
    """Fetches historical data up to today for training."""
    ticker = STOCK_TICKERS.get(stock_name)
    if not ticker:
        raise ValueError("Invalid stock name provided.")

    # Fetch slightly more than 'years' to be safe, end one day after today
    end_date = date.today() + timedelta(days=1)
    start_date = date.today() - timedelta(days=years*365 + 5) # Start 5 days earlier

    try:
        print(f"Fetching data for {ticker} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}") # Debug print
        df = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        df.reset_index(inplace=True)
        df = df.dropna()
    except Exception as e:
         print(f"yfinance download failed: {e}") # Debug print for download errors
         raise ValueError(f"Failed to download data for {stock_name} ({ticker}). Error: {e}")


    if df.empty:
        # Raise the error again if still empty after download attempt
        raise ValueError(f"No data found for {stock_name} ({ticker}) between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}.")

    # Ensure correct column names if MultiIndex was returned previously
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip('_') if col[1] else col[0] for col in df.columns.values]
        # Rename columns to simple names if needed
        df = df.rename(columns={f'Date_': 'Date', f'Open_{ticker}': 'Open', f'High_{ticker}': 'High',
                                f'Low_{ticker}': 'Low', f'Close_{ticker}': 'Close', f'Volume_{ticker}': 'Volume'})

    df['Date'] = pd.to_datetime(df['Date']) # Ensure Date is datetime object
    # Filter df to ensure it doesn't go beyond today's actual date if extra days were fetched
    df = df[df['Date'] <= pd.to_datetime(date.today())]

    return df

def estimate_confidence(model_name, last_historical_date, prediction_date_dt, historical_df, model, days_to_predict=1):
    """Estimates model confidence based on error on recent historical data and extrapolation distance."""
    days_diff = (prediction_date_dt - last_historical_date).days

    if len(historical_df) < 30: # Not enough data for robust confidence
        return "Very Low"

    train_size = max(30, int(len(historical_df) * 0.8)) # At least 30 days, or 80%
    recent_X = historical_df['Day'].iloc[-train_size:].values.reshape(-1, 1)
    recent_y = historical_df['Close'].iloc[-train_size:].values

    if len(recent_X) > 1 and len(recent_y) > 1: # Need at least 2 points
        if model_name == 'Linear Regression':
            if days_diff > 365: return "Very Low"
            if days_diff > 180: return "Low"
            if days_diff > 90: return "Medium"
            return "Medium-High"
        else: # RF, XGBoost
            if days_diff > 365: return "Very Low"
            if days_diff > 180: return "Low"
            if days_diff > 90: return "Medium"
            if days_diff > 30: return "Medium-High"
            return "High"

    return "Low" # Default if insufficient data

def train_and_predict(stock_name, model_name, prediction_date_str):
    """
    Fetches data, trains, predicts a single future date, estimates confidence,
    and also generates a short-term future trend for charting.
    """
    try:
        # 1. Validate Prediction Date
        try:
            prediction_date_dt = datetime.strptime(prediction_date_str, '%Y-%m-%d').date()
            if prediction_date_dt <= date.today():
                 return {'error': "Prediction date must be in the future."}
        except ValueError as e:
            return {'error': f"Invalid date format or value: {e}"}

        # 2. Fetch Historical Data
        df = fetch_historical_data(stock_name, years=2)
        if df.empty:
            return {'error': f"Could not fetch sufficient historical data for {stock_name}."}

        last_historical_date = df['Date'].iloc[-1].date()

        # 3. Feature Engineering
        df['Day'] = (df['Date'] - df['Date'].min()).dt.days
        X_train = df[['Day']]
        y_train = df['Close']

        # 4. Train Model
        model = get_model(model_name)
        model.fit(X_train, y_train)

        # 5. Predict Single Future Price (for the main display)
        prediction_day_num = (prediction_date_dt - df['Date'].min().date()).days
        # --- CAST TO FLOAT HERE ---
        predicted_price_main = float(model.predict(np.array([[prediction_day_num]]))[0])
        # --- End of change ---

        # 6. Estimate Confidence
        confidence = estimate_confidence(model_name, last_historical_date, prediction_date_dt, df, model)

        # 7. Generate Data for Charts
        #    a) Historical Trend Data (Last 30 Days)
        historical_30_days = df.tail(30).copy()
        historical_30_data = {
            'x': historical_30_days['Date'].dt.strftime('%Y-%m-%d').tolist(),
            # --- Ensure historical y-values are standard floats ---
            'y': [float(p) for p in historical_30_days['Close'].tolist()],
        }

        #    b) Full Historical Trend Data
        full_historical_data = {
            'x': df['Date'].dt.strftime('%Y-%m-%d').tolist(),
            # --- Ensure historical y-values are standard floats ---
            'y': [float(p) for p in df['Close'].tolist()],
        }

        #    c) Predicted Trend Data
        future_days_for_trend = 15
        future_dates = [prediction_date_dt + timedelta(days=i) for i in range(future_days_for_trend + 1)]
        future_day_nums = [(d - df['Date'].min().date()).days for d in future_dates]
        # --- CAST EACH PREDICTED PRICE TO FLOAT HERE ---
        predicted_future_prices = [float(p) for p in model.predict(np.array(future_day_nums).reshape(-1, 1)).tolist()]
        # --- End of change ---

        predicted_trend_data = {
            'x': [d.strftime('%Y-%m-%d') for d in future_dates],
            # Use the already converted list, but round for display/logging consistency
            'y': [round(p, 2) for p in predicted_future_prices],
        }

        # 8. Prepare results dictionary with standard floats
        result_data = {
            'predicted_date': prediction_date_str,
            'prediction_model': model_name,
            'stock_name': stock_name,
            # Use the converted float, round for display/logging consistency
            'predicted_price': round(predicted_price_main, 2),
            'confidence': confidence,
            'historical_30_data': historical_30_data,
            'full_historical_data': full_historical_data,
            'predicted_trend_data': predicted_trend_data,
        }

        return result_data

    except Exception as e:
        print(f"Error in ML logic: {e}")
        traceback.print_exc()
        return {'error': f"An unexpected error occurred: {str(e)}"}