from aiAnalyzer.deep_research import aiAnalyzeTopFiveStocks
from list_stocks import get_50_stocks
from final_strat import final_strategy



print("Calling Stat Analasis")

for stock in get_50_stocks()[:10]:
    final_strategy(1000, stock)

print("Calling AI")
aiAnalyzeTopFiveStocks()



