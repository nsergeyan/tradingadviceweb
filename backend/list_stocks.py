#https://datahub.io/core/s-and-p-500-companies-financials

import os
import csv
import yfinance as yf
from datetime import datetime

def get_50_stocks() -> list:
    """
    Returns a list of the symbols of the 50 most traded stocks in the last full week
    :return: List of 50 most traded symbols
    """
    print("Fetching stocks")
    path = os.path.join(os.path.dirname(__file__),'DB for stock update/stocks_volume.csv')
    with open(path, 'r') as file:

        current_week = datetime.now().isocalendar()[1] #Returns the week number

        reader = csv.reader(file)
        last_update = int(next(reader)[0])

        #Updates our stock volume csv for the current week if its out of date
        if last_update != current_week:
            print("Stock list out of date, updating")
            update_stock_volume()

        next(reader) #Skips header

        valid_rows = [row for row in reader if row and len(row) > 1 and row[1].strip()] #removes whitespcases and empty records
        sorted_rows = sorted(list(valid_rows), key = lambda i : float(i[1]), reverse= True)

        return [item[0] for item in sorted_rows[:50]]


def update_stock_volume() -> None:
    """
    Updates in place the csv containing the volume of the stocks (stock_volume.csv) with the data stocks from stocks.csv
    """
    print("Updating stock csv")

    #Reads the 500 stocks in the S&P 500
    path = os.path.join(os.path.dirname(__file__), 'DB for stock update/stocks.csv')
    with open(path, 'r') as file:
        reader = csv.reader(file)
        next(reader)

        data = [row[0] for row in reader]


    #Writes to the CSV the stock symbol and the trade volume of the last week
    path = os.path.join(os.path.dirname(__file__), "DB for stock update/stocks_volume.csv")
    with open(path, "w", newline="") as f:

        writer = csv.writer(f)
        writer.writerow([datetime.now().isocalendar()[1]])
        writer.writerow(["Symbol", "Volume"])

        for symbol in data:
            stock = yf.Ticker(symbol)
            last_week = stock.history(period="1wk", interval="1wk")

            if last_week.empty:
                continue

            #We grab the last full week ([-1]), sles it would return this week so far
            writer.writerow([symbol, last_week.iloc[-1]["Volume"]])


if __name__ == "__main__":
    print(get_50_stocks())