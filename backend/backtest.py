import pandas as pd
import numpy as np
from statsmodels.tsa.api import VAR
from statsmodels.tsa.arima.model import ARIMA
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
    """
    df_num = df[["open", "high", "low", "close", "volume"]].astype(float)
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

    # error metrics
    errors = test - forecast_df
    mae = errors.abs().mean()
    rmse = np.sqrt((errors ** 2).mean())
    mape = (errors.abs() / test.replace(0, np.nan)).mean() * 100

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


def backtest_arima_close(df: pd.DataFrame, order=(5, 1, 0), train_ratio: float = 0.8):
    """
    Backtest ARIMA model only on 'close' column.
    """
    df_close = df["close"].astype(float)
    train, test = train_test_split_timeseries(df_close, train_ratio)

    # fit ARIMA
    model = ARIMA(train, order=order)
    results = model.fit()

    # forecast
    forecast = results.forecast(steps=len(test))
    forecast.index = test.index

    # error metrics
    errors = test - forecast
    mae = errors.abs().mean()
    rmse = np.sqrt((errors ** 2).mean())
    mape = (errors.abs() / test.replace(0, np.nan)).mean() * 100

    correctness = (test >= forecast).mean()

    metrics = {
        "MAE": mae,
        "RMSE": rmse,
        "MAPE (%)": mape,
        "Correctness Rate": correctness,
    }

    forecast_df = pd.DataFrame({"close": forecast}, index=test.index)

    return forecast_df, test, metrics


if __name__ == "__main__":
    from backend.database import fetch_ohlcv

    df = fetch_ohlcv("IBM", "Weekly", limit=200)

    # VAR backtest
    forecast_var, actual_var, metrics_var = backtest_var_with_metrics(df, maxlags=2)

    print("\n[VAR] Error Metrics:")
    for k, v in metrics_var.items():
        print(k, ":", v)

    # ARIMA backtest (only close price)
    forecast_arima, actual_arima, metrics_arima = backtest_arima_close(df, order=(5, 1, 0))

    print("\n[ARIMA] Error Metrics (close only):")
    print(metrics_arima)

    print("\nLast 5 rows comparison (close):")
    result_close = pd.concat([actual_arima, forecast_arima], axis=1, keys=["Actual", "Predicted"])
    print(result_close.tail(5))
