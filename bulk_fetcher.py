# bulk_fetcher.py

from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from data_fetcher import fetch_stock_data,previous_day_data

def bulk_fetch_intraday(symbols, max_workers=3, batch_size=8, sleep_time=0.8):
    """
    SAFE bulk fetch for Dhan (rate-limit friendly)
    """
    results = {}

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(fetch_stock_data, symbol): symbol
                for symbol in batch
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    data = future.result()
                    if data is not None:
                        results[symbol] = data
                except Exception as e:
                    print(f"❌ Error fetching {symbol}: {e}")

        # ✅ IMPORTANT: cooldown between batches
        time.sleep(sleep_time)

    print(f"✅ Intraday fetched: {len(results)} / {len(symbols)}")
    return results


def bulk_fetch_previous_day(symbols, max_workers=2, batch_size=6, sleep_time=1.0):
    results = {}

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(previous_day_data, symbol): symbol
                for symbol in batch
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    data = future.result()
                    if data is not None:
                        results[symbol] = data
                except Exception as e:
                    print(f"❌ Prev-day error {symbol}: {e}")

        time.sleep(sleep_time)

    print(f"✅ Prev-day fetched: {len(results)} / {len(symbols)}")
    return results
