from backend.aiAnalyzer.deep_research import aiAnalyzeTopFiveStocks
from backend.list_stocks import get_50_stocks
from backend.final_strat import final_strategy



print("Calling Stat Analasis")

for stock in get_50_stocks()[:5]:
    final_strategy(1000, stock)
    print("\n")

print("\n\n")

print("Calling AI")
aiAnalyzeTopFiveStocks()



