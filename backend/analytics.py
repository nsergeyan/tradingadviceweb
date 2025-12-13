import pandas as pd
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.api import VAR

from backend.database import fetch_ohlcv


def predict_next_ohlcv(df: pd.DataFrame, maxlags: int = 2, alpha: float = 0.05):
    """
    Predict the next OHLCV values using VAR model (with normalization) and return prediction + confidence intervals.

    Args:
        df (pd.DataFrame): Historical OHLCV data with columns ["open", "high", "low", "close", "volume"].
        maxlags (int): Maximum lag order for VAR model (default=2).
        alpha (float): Significance level for confidence interval (default=0.05 → 95% CI).

    Returns:
        forecast_df (pd.DataFrame): Predicted OHLCV values for the next step (original scale).
        lower_df (pd.DataFrame): Lower bound of the confidence intervals (original scale).
        upper_df (pd.DataFrame): Upper bound of the confidence intervals (original scale).
    """
    # Keep only numeric OHLCV columns
    df_num = df[["open", "high", "low", "close", "volume"]].astype(float)

    # Standardize the data
    scaler = StandardScaler()
    scaled = scaler.fit_transform(df_num)

    # Build and fit VAR model
    model = VAR(scaled)
    results = model.fit(maxlags=maxlags)

    # Forecast with confidence intervals
    lag_order = results.k_ar
    forecast, lower, upper = results.forecast_interval(
        scaled[-lag_order:], steps=1, alpha=alpha
    )

    # Inverse transform back to original scale
    forecast_rescaled = scaler.inverse_transform(forecast)
    lower_rescaled = scaler.inverse_transform(lower)
    upper_rescaled = scaler.inverse_transform(upper)

    forecast_df = pd.DataFrame(forecast_rescaled, columns=df_num.columns)
    lower_df = pd.DataFrame(lower_rescaled, columns=df_num.columns)
    upper_df = pd.DataFrame(upper_rescaled, columns=df_num.columns)

    return forecast_df, lower_df, upper_df


# ---------------- Example usage ----------------
if __name__ == "__main__":
    df = fetch_ohlcv("IBM", "Weekly", limit=100)

    forecast, lower, upper = predict_next_ohlcv(df, maxlags=2)

    print("Next OHLCV prediction:")
    print(forecast)
    print("\n95% Confidence intervals:")
    print("Lower bound:\n", lower)
    print("Upper bound:\n", upper)
