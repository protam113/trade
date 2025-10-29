import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "src")
ROOT = os.path.abspath(ROOT)
sys.path.append(ROOT)

print("ROOT:", ROOT)
print("Folders:", os.listdir(ROOT))

import asyncio

from aiomql import MetaTrader


async def main():
    mt5 = MetaTrader()
    res = await mt5.initialize(login=52575885, password='@q30SMKYhawwOa', server='ICMarketsSC-Demo')
    if not res:
        print('Unable to login and initialize')
        return 
    # get account information
    acc = await mt5.account_info()
    print(acc)
    # get symbols
    symbols = await mt5.symbols_get()
    print(symbols)
    
asyncio.run(main())