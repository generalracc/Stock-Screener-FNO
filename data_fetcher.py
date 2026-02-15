import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dhanhq import dhanhq
import logging
import time
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
max_retries=2
client_id = '1100467218'
access_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzcxMjU5MzczLCJpYXQiOjE3NzExNzI5NzMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwNDY3MjE4In0.SRoHGEzUtri_cvycrZY2ht-z_IRdaLZjmKb4iwMLcg-X-GVqDP_ItEPoCO3g0GHhLyFuMSjEpf29JPDiVJAozQ'
# dhan = dhanhq(client_id, access_token)
stock_data = pd.read_csv('updated_list.csv')
def get_security_id(symbol: str) -> int:
        """Retrieve the security ID for a given stock symbol."""
        match = stock_data[stock_data['Symbol'] == symbol]
        if match.empty:
            raise ValueError(f"Symbol {symbol} not found in the CSV file.")
        return int(match['SECURITY_ID'].iloc[0]) 
def previous_day_data(symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data with retry mechanism"""
        # Convert interval string to Dhan format

        

        for attempt in range(max_retries):
            try:
                # Convert dates to required format if needed
                # from_date = start_date.strftime('%Y-%m-%d')
                # to_date = end_date.strftime('%Y-%m-%d')
                
                # Fetch historical data using Dhan API
                security_id = get_security_id(symbol)
                logger.info(f"Fetching data for Symbol: {symbol} (Security ID: {security_id})")
                current_date=datetime.now()
                previous_date = current_date - timedelta(days=30)
                today_Date=current_date.strftime("%Y-%m-%d")
                last_day=previous_date.strftime("%Y-%m-%d")
                # previous_date = current_date - timedelta(days=1)
                dhan = dhanhq(client_id, access_token) 
                data = dhan.historical_daily_data(
                    security_id=security_id,
                    exchange_segment='NSE_EQ',
                    instrument_type='EQUITY',
                    expiry_code=0,
                    from_date=last_day,
                    to_date=today_Date
                )
                
              
                
                # Convert to DataFrame and format
                df = pd.DataFrame(data['data'])
                # df['Datetime'] = pd.to_datetime(df['datetime'])
                temp_list=[]
                for i in df['timestamp']:
                    temp=dhan.convert_to_date_time(i)
                    temp_list.append(temp)
                df['Date']=temp_list
                # df.set_index('Datetime', inplace=True)
                # print(df)
         
                return df
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {security_id}: {str(e)}")
def _fetch_with_retry(security_id: int) -> Optional[pd.DataFrame]:
        interval_map = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '1d': 'DAY'
        }

        for attempt in range(max_retries):
            try:
                current_date = datetime.now()
                today_Date = current_date.strftime("%Y-%m-%d")

                # Add delay between retries that increases with each attempt
                if attempt > 0:
                    time.sleep(0.5)  # 2, 4, 6 seconds between retries
                dhan = dhanhq(client_id, access_token) 
                data = dhan.intraday_minute_data(
                    security_id=security_id,
                    exchange_segment='NSE_EQ',
                    instrument_type='EQUITY',
                    interval=1,
                    from_date=today_Date,
                    to_date=today_Date
                )
                # data = dhan.historical_daily_data(
                #     security_id=security_id,
                #     exchange_segment='NSE_EQ',
                #     instrument_type='EQUITY',
                #     expiry_code=0,
                #     from_date="2025-01-11",
                #     to_date="2025-02-11"
                # )

                # More thorough validation of API response
                if not data or not isinstance(data, dict) or 'data' not in data:
                    logger.warning(f"Attempt {attempt + 1}: Invalid API response structure for {security_id}")
                    continue

                if not data['data']:
                    logger.warning(f"Attempt {attempt + 1}: Empty data array for {security_id}")
                    continue

                df = pd.DataFrame(data['data'])
                
                # Validate we got the expected columns
                required_columns = ['timestamp', 'open', 'high', 'low', 'close']
                if not all(col in df.columns for col in required_columns):
                    logger.warning(f"Attempt {attempt + 1}: Missing required columns in data for {security_id}")
                    continue

                temp_list = [dhan.convert_to_date_time(i) for i in df['timestamp']]
                df['Date'] = temp_list

                # Additional validation - check for reasonable data
                if len(df) < 5:  # Expecting at least 5 data points
                    logger.warning(f"Attempt {attempt + 1}: Insufficient data points for {security_id}")
                    continue

                return df

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {security_id}: {str(e)}")
                time.sleep(1)  # wait before retry

        logger.error(f"All {max_retries} attempts failed for security_id {security_id}")
        return None

def fetch_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    try:
        security_id = get_security_id(symbol)
        logger.info(f"Fetching data for Symbol: {symbol} (Security ID: {security_id})")

        data = _fetch_with_retry(security_id)

        if data is not None and not data.empty:
            # ✅ PRINT SUCCESSFUL FETCH
            print(f"✅ DHAN DATA FETCHED: {symbol} | candles = {len(data)}")

            return data

        print(f"❌ NO DATA FROM DHAN: {symbol}")
        return None

    except Exception as e:
        print(f"❌ ERROR FETCHING {symbol}: {e}")
        return None
# fetch_stock_data("JINDALSTEL")
