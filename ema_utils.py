import pandas as pd

def calculate_ema(series: pd.Series, period: int):
    return series.ewm(span=period, adjust=False).mean()


def ema_condition(df, direction):
    df['EMA_9'] = calculate_ema(df['close'], 9)
    df['EMA_15'] = calculate_ema(df['close'], 15)

    last = df.iloc[-1]

    if direction == "UP":
        return last['EMA_9'] > last['EMA_15']
    else:
        return last['EMA_9'] < last['EMA_15']
