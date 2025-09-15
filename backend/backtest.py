import pandas as pd
import numpy as np
from statsmodels.tsa.api import VAR
from sklearn.preprocessing import StandardScaler


def train_test_split_timeseries(df: pd.DataFrame, train_ratio: float = 0.8):
    """Split time series into train/test sets (no shuffle)."""
    n_train = int(len(df) * train_ratio)
    train = df.iloc[:n_train]
    test = df.iloc[n_train:]
    return train, test


def backtest_var_with_metrics(df: pd.DataFrame, maxlags: int = 2, train_ratio: float = 0.8):
    """
    Backtest VAR model with normalization. Return forecast, actual, and error metrics.

    Args:
        df (pd.DataFrame): OHLCV DataFrame with ["open","high","low","close","volume"]
        maxlags (int): Lag order for VAR
        train_ratio (float): Training set ratio

    Returns:
        forecast_df (pd.DataFrame): Predicted values (original scale)
        actual_df (pd.DataFrame): Actual test values (original scale)
        metrics (dict): Error metrics and correctness rate
    """
    # ensure numeric
    df_num = df[["open", "high", "low", "close", "volume"]].astype(float)

    # split
    train, test = train_test_split_timeseries(df_num, train_ratio)

    # normalize
    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(train)
    test_scaled = scaler.transform(test)

    # fit model on scaled data
    model = VAR(train_scaled)
    results = model.fit(maxlags=maxlags)

    # forecast (scaled)
    lag_order = results.k_ar
    forecast_scaled = results.forecast(train_scaled[-lag_order:], steps=len(test))

    # inverse transform back to original scale
    forecast = scaler.inverse_transform(forecast_scaled)

    forecast_df = pd.DataFrame(forecast, columns=df_num.columns, index=test.index)

    # error metrics (on original scale)
    errors = test - forecast_df
    mae = errors.abs().mean()
    rmse = np.sqrt((errors ** 2).mean())
    mape = (errors.abs() / test.replace(0, np.nan)).mean() * 100

    # correctness rate
    correctness = {}
    for col in ["open", "high", "low", "close"]:
        correctness[col] = (test[col] >= forecast_df[col]).mean()

    metrics = {
        "MAE": mae.to_dict(),
        "RMSE": rmse.to_dict(),
        "MAPE (%)": mape.to_dict(),
        "Correctness Rate": correctness,
    }

    return forecast_df, test, metrics


if __name__ == "__main__":
    from backend.database import fetch_ohlcv

    df = fetch_ohlcv("IBM", "Weekly", limit=200)

    forecast, actual, metrics = backtest_var_with_metrics(df, maxlags=2)

    print("\nError Metrics:")
    for k, v in metrics.items():
        print(k, ":", v)

    print("\nLast 5 rows (Actual vs Predicted):")
    result = pd.concat([actual, forecast], axis=1, keys=["Actual", "Predicted"])
    print(result.tail(5))
