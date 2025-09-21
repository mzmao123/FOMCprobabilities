import os
import pandas as pd
from datetime import datetime as dt
import argparse
#This is to save historical fed funds data into my data folder (because stooq seems to only save 1 month of data into the past)
monthCodes ={'january':'F','february':'G','march':'H','april':'J',
'may':'K','june':'M','july':'N','august':'Q','september':'U',
'october':'V','november':'X','december':'Z'}
fomcDates=[dt.strptime(x, '%m/%d/%y') for x in ["7/30/25","9/16/25", "10/19/25", "12/10/25", 
"1/28/26", "3/18/26", "4/29/26", "6/17/26", "7/29/26", "9/16/26", "10/28/26", "12/9/26", "1/27/27", 
"3/17/27", "4/28/27",  "6/9/27", "7/28/27", "9/15/27", "10/27/27", "12/8/27"]]
monthDict = {1:"january",2:"february",3:"march",4:"april",5:"may",6:"june",7:"july",8:"august",9:"september",10:"october",11:"november",12:"december"}

class DataSaver():
    def __init__(self, month: str, year: str) -> None:
        date = dt.strptime(dt.now().strftime("%m/%y"), "%m/%y")
        '''
        if len(year) != 2:
            if len(year) == 4:
                year = str(year)[2:4]
            else:
                return ValueError("Year must be 2 or 4 digits!")
        '''
        if len(year) == 4:
                year = str(year)[2:4]
        '''
        if dt.strptime(str(month) + "/" + str(year), "%m/%y") >= date:
            return ValueError("Month and year do not need to be saved yet!")'''

        self.month = month
        self.year = year
        self.ticker = self.getTicker()
        self.df = self.getDataForTicker()
        self.df.set_index('Date', inplace=True)

    def getTicker(self) -> str:
        ticker = f"zq{monthCodes[monthDict[int(self.month)]].lower()}{str(self.year)}.f"
        return ticker

    def getURL(self) -> str:
            return f"https://stooq.com/q/l/?s={self.ticker}&f=sd2t2ohlcv&h&e=csv"

    def getDataForTicker(self) -> pd.DataFrame:
        df = pd.read_csv(self.getURL())
        return df
def main(month, year):
    data = DataSaver(month, year)
    print(data.getURL())
    data.df.to_csv(os.path.join(os.path.dirname(__file__), "data", f"{data.ticker[:5]}.csv"))

if __name__ == "__main__":
    main(month, year)