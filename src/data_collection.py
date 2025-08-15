import yfinance as yf
from pytrends.request import TrendReq
import requests
import pandas as pd
import time
import random
from bs4 import BeautifulSoup
import numpy as np


# --- Yahoo Finance Data Collection ---
def get_yahoo_finance_data(ticker, start_date, end_date):
    """
    Fetches historical stock data from Yahoo Finance for a given ticker and date range.
    Ensures the DataFrame has the correct structure and calculates log daily returns.

    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL').
        start_date (str): The start date in 'YYYY-MM-DD' format.
        end_date (str): The end date in 'YYYY-MM-DD' format.

    Returns:
        pandas.DataFrame: A DataFrame containing historical stock data with the correct schema, or None if an error occurs.
    """
    print(f"Attempting to fetch Yahoo Finance data for {ticker} from {start_date} to {end_date}...")
    try:
        # Download historical data using yfinance
        data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=True)
        if not data.empty:
            print(f"Successfully fetched {len(data)} rows of Yahoo Finance data for {ticker}.")

            # Reset index to make 'Date' a column
            data.reset_index(inplace=True)

            # Dynamically check and rename columns
            expected_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            missing_columns = [col for col in expected_columns if col not in data.columns]
            if missing_columns:
                raise ValueError(f"Missing columns in data: {missing_columns}")

            # Calculate log daily returns
            data['LOG_RETURNS'] = np.log(data['Close'] / data['Close'].shift(1))

            # Ensure the DataFrame has the correct schema
            data = data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'LOG_RETURNS']]
            data.columns = ['DATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME', 'LOG_RETURNS']

            print(f"Data for {ticker} formatted with the correct schema.")
            return data
        else:
            print(f"No Yahoo Finance data found for {ticker} in the specified range.")
            return None
    except Exception as e:
        print(f"Error fetching Yahoo Finance data for {ticker}: {e}")
        return None


# --- Polygon.io Data Collection ---
def get_polygon_data(ticker, start_date, end_date, api_key, multiplier=1, timespan='day'):
    """
    Fetches historical aggregate (OHLCV) data from Polygon.io for a given ticker and date range.

    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL').
        start_date (str): The start date in 'YYYY-MM-DD' format.
        end_date (str): The end date in 'YYYY-MM-DD' format.
        api_key (str): Your Polygon.io API key.
        multiplier (int): The size of the timespan multiplier. (e.g., 1 for 1 day, 5 for 5 days)
        timespan (str): The size of the time period. (e.g., 'day', 'week', 'month', 'year', 'minute', 'hour')

    Returns:
        pandas.DataFrame: A DataFrame containing historical OHLCV data, or None if an error occurs.
    """
    print(f"Attempting to fetch Polygon.io data for {ticker} from {start_date} to {end_date}...")
    # Polygon.io aggregates endpoint
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{start_date}/{end_date}"
    params = {
        "apiKey": api_key,
        "sort": "asc",
        "limit": 50000 # Max limit for aggregates
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if data and data.get('results'):
            df = pd.DataFrame(data['results'])
            # Rename columns to a more standard format (Open, High, Low, Close, Volume)
            df = df.rename(columns={
                'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume',
                't': 'Timestamp', 'n': 'Transactions'
            })
            # Convert timestamp to datetime and set as index
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
            df = df.set_index('Timestamp')
            print(f"Successfully fetched {len(df)} rows of Polygon.io data for {ticker}.")
            return df[['Open', 'High', 'Low', 'Close', 'Volume']] # Return standard OHLCV
        elif data.get('status') == 'NOT_FOUND' or not data.get('results'):
            print(f"No Polygon.io data found for {ticker} in the specified range or ticker not found.")
            return None
        else:
            print(f"Polygon.io API error for {ticker}: {data.get('error') or data.get('message', 'Unknown error')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Polygon.io data for {ticker}: {e}")
        print("Please check your API key, internet connection, or Polygon.io rate limits.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while fetching Polygon.io data for {ticker}: {e}")
        return None


# --- Google Trends Data Collection ---
def get_google_trends_data(keyword, timeframe='today 3-m'):
    """
    Fetches Google Trends interest over time for a given keyword.

    Args:
        keyword (str): The search keyword (e.g., 'Apple Inc' or 'AAPL').
        timeframe (str): The time frame for the trend data (e.g., 'today 3-m', '2023-01-01 2024-01-01').

    Returns:
        pandas.DataFrame: A DataFrame containing interest over time, or None if an error occurs.
    """
    print(f"Attempting to fetch Google Trends data for '{keyword}' with timeframe '{timeframe}'...")
    try:
        pytrends = TrendReq(hl='en-US', tz=360) # hl: host language, tz: timezone offset
        pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo='', gprop='')
        data = pytrends.interest_over_time()
        if not data.empty and keyword in data.columns:
            # Drop the 'isPartial' column if it exists
            if 'isPartial' in data.columns:
                data = data.drop(columns=['isPartial'])
            print(f"Successfully fetched Google Trends data for '{keyword}'.")
            return data
        else:
            print(f"No Google Trends data found for '{keyword}' or keyword column missing.")
            return None
    except Exception as e:
        print(f"Error fetching Google Trends data for '{keyword}': {e}")
        print("Note: pytrends is an unofficial scraper and can be unreliable. Consider using Glimpse API for production.")
        return None

# --- StockTwits Data Collection ---
def get_stocktwits_data(ticker, limit=50):
    """
    Fetches recent messages from StockTwits for a given ticker.

    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL').
        limit (int): The maximum number of messages to retrieve (default is 50, max is 200).

    Returns:
        list: A list of dictionaries, each representing a StockTwits message, or an empty list if an error occurs.
    """
    print(f"Attempting to fetch StockTwits data for {ticker} (limit: {limit})...")
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    params = {"limit": min(limit, 200)} # StockTwits API max limit is 200 messages per request

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        messages = []
        if data and 'messages' in data:
            for msg in data['messages']:
                message_info = {
                    "id": msg.get("id"),
                    "body": msg.get("body"),
                    "created_at": msg.get("created_at"),
                    "user_username": msg.get("user", {}).get("username"),
                    "user_id": msg.get("user", {}).get("id"),
                    "symbols": [s.get("symbol") for s in msg.get("symbols", [])],
                    "sentiment": msg.get("entities", {}).get("sentiment", {}).get("basic")
                }
                messages.append(message_info)
            print(f"Successfully fetched {len(messages)} StockTwits messages for {ticker}.")
        else:
            print(f"No messages found for {ticker} on StockTwits.")
        return messages
    except requests.exceptions.RequestException as e:
        print(f"Error fetching StockTwits data for {ticker}: {e}")
        print("Note: Ensure you are not exceeding StockTwits API rate limits.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while fetching StockTwits data for {ticker}: {e}")
        return []


