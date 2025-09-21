import pandas as pd
import numpy as np
import math
from datetime import datetime as dt
from calendar import monthrange
import holidays
import pandas_datareader.stooq as stooq
import pandas_datareader as pdr
import os
import calendar

import importlib, monthFind
importlib.reload(monthFind)
from monthFind import FOMCfinder

class fedWatch():
    def __init__(self, targetDate: dt, fomcDates: list, numProjections: int, currentLowerFFRLimit: float, currentUpperFFRLimit: float) -> None:
        self.meetingData = FOMCfinder(targetDate, fomcDates, numProjections).createFOMCDataFrame()
        self.targetDate = targetDate
        self.lowerLimit = currentLowerFFRLimit
        self.upperLimit = currentUpperFFRLimit
    
    def fedFundsGrab(self, ticker: str) -> pd.DataFrame:
        #it would probably be better to use a seperate module/method for this but for now I don't have the best data pipeline so this is what I will be implementing
        tickToMonth = {'f': 'january', 'g': 'february', 'h': 'march', 'j': 'april', 'k': 'may', 'm': 'june', 
        'n': 'july', 'q': 'august', 'u': 'september', 'v': 'october', 'x': 'november', 'z': 'december'}
        monthToNum = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7, 
        'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}

        #if the ticker is for a month before the current/target date, we will pull our data from locally stored data (because stooq doesnt seem to save past fed funds contracts)
        monthNum = monthToNum[tickToMonth[ticker[2]]]
        yearNum = int(ticker[3:5])
        tickerDate = dt.strptime(f"{monthNum}/{yearNum}", "%m/%y")

        if tickerDate < self.targetDate:
            priceDf = pd.read_csv(os.path.join(os.path.dirname(__file__), "data", f"{ticker[:5]}.csv"))
        else:
            URL =  f"https://stooq.com/q/l/?s={ticker}&f=sd2t2ohlcv&h&e=csv"
            priceDf = pd.read_csv(URL)

        #now we want to make date the index and a datetime object
        priceDf.set_index("Date", inplace=True)
        priceDf.index = pd.to_datetime(priceDf.index, format = "%Y-%m-%d")

        return priceDf
    
    def populatePriceData(self):
        #we now want to add the start, avg, and close prices for each month
        #for this first part we will fill in the avg price using the fed funds contract price for today
        #then if the month is a non fomc meeting month, the starting and ending prices will be the same as the avg price
        priceStart = []
        priceAvg = []
        priceEnd = []

        for row in self.meetingData.iterrows():
            #date, ticker, meetingdate, order
            contractDate = row[1][0]
            ticker = row[1][1]
            meetingDate = row[1][2]

            priceData = self.fedFundsGrab(ticker)
            closePrice = priceData.iloc[0,5]
            priceAvg.append(closePrice)

            if meetingDate == "No Meeting":
                priceStart.append(closePrice)
                priceEnd.append(closePrice)

            else:
                priceStart.append(float(0))
                priceEnd.append(float(0))
        

        #we now want to fill in the start an end prices for the non fomc meeting months

        #first we fill forward if the month is after a non fomc meeting month, since we have defined our endpoints to be non fomc meeting months we can ignore them (they are already filled in)
        for i in range(1, len(priceAvg)-1):
            if priceStart[i] == 0 and priceEnd[i-1] != 0:
                priceStart[i] = priceEnd[i-1]
            if priceEnd[i] == 0 and priceStart[i+1] != 0:
                priceEnd[i] = priceStart[i+1]

        #now we fill in from the back, if the end price is 0 then it is the same as the start price of the next month. 
        #if the start price is 0, then we can cacluate the start price using the formula from the fedWatch paper (essentially a weighted average)
        for i in reversed(range(1, len(priceAvg) - 1)):
            if priceEnd[i] == 0.0:
                priceEnd[i] = priceStart[i + 1]

            if priceStart[i] == 0.0:
            
                #here we calculate the start price using the formula from the fedWatch paper
                date = dt.strptime(self.meetingData["Meeting Date"][i], "%m/%d/%y")
                daysInMonth = calendar.monthrange(date.year, date.month)[1]
                m = daysInMonth - date.day + 1 #days in month after a FOMC meeting
                n = daysInMonth - m #days in monthbefore a FOMC meeting, including the meeting date
                total = m + n  # or p_avg[i], depending on your preference
                priceStart[i] = (priceAvg[i] -((m / total) * priceEnd[i])) / (n / total)
        #
        
        self.meetingData["priceStart"] = priceStart
        self.meetingData["priceAvg"] = priceAvg
        self.meetingData["priceEnd"] = priceEnd
        
        
        return priceStart, priceAvg, priceEnd

    def rateChangeInfo(self):

        self.populatePriceData()
        
        changeDf = self.meetingData.copy()
        changeDf = changeDf[(changeDf['Order'] >0)]

        changeDf['Rate Change'] = (((100-changeDf['priceEnd'])-(100-changeDf['priceStart']))/25)*100 #this gives us the number of rate hikes/cuts implied by contracts for each month

        #as described in the FedWatch paper, we want to be looking at binary buckets for hikes, so we will be using two variables to represent two adjacent 25bps buckets

        changeDf["Bucket1"] = changeDf["Rate Change"].apply(lambda x: int(np.sign(x)*math.floor(np.abs(x))*25)) #this bucket is for the leading digits of the rate change, i.e for 2.6 --> 2.0
        changeDf["Bucket2"] = changeDf["Rate Change"].apply(lambda x: int(np.sign(x)*math.floor(np.abs(x))*25 + 25*np.sign(x))) #this bucket is for the trailing digits of the rate change, i.e for 2.6 --> 0.6 and for -2.6 --> -0.6

        #now we calculate the probabilities implied by each of these buckets, the calculations are also based on the FedWatch paper
        #if the rate change number >=1 , then probability of hike for bucket 1 is 1, otherwise it is 0 and we got to the fractional part of the hike: bucket 2
        #in bucket 2, we know that the probability of a hike for the decimal part is essentially just the decimal part its self, for 2.6 --> p(hike 1) = 1 and p(hike 2 ) = 0.6

        changeDf['Prob1'] = changeDf['Rate Change'].apply(lambda x: 1-(np.abs(x)-math.trunc(np.abs(x)))) 
        changeDf['Prob2'] = changeDf['Rate Change'].apply(lambda x: (np.abs(x)-math.trunc(np.abs(x))))

        #now we have two buckets and their probabilites. ex. 60 bps implied hike
        #bucket 1 = 50bps and bucket 2 = 10bps
        #market implied probability of 50 bps hike (p(bucket 1)) =1 and market implied probability of a 75 bps hike is 0.4 (60/50 = 2.4)

        return changeDf
        #now we can convert these binary buckets and probabilities into a cumulative distribution for the implied rate path up to the number of meetings we want to project

    def cumulativeDistribution(self):

        changeDf = self.rateChangeInfo()
        changeDict = {}

        cols = changeDf.columns
        for row in changeDf.iterrows():

            meetingDate = row[1][cols.get_loc("Meeting Date")]

            meeetingSize = np.array(row[1][[cols.get_loc("Bucket1"), cols.get_loc("Bucket2")]])
            meetingProb = np.array(row[1][[cols.get_loc("Prob1"), cols.get_loc("Prob2")]])

            changeDict[meetingDate] = (meeetingSize, meetingProb)
        
        
        dates = [dt.strptime(date, '%m/%d/%y') for date in changeDict.keys()]
        dates = sorted(dates)

        #we now want to create a dataframe containing the cumulative distribution of each meeting (we do this by starting with the first upcoming meeting and then moving on from there)

        meetingDate = min(dates).strftime('%m/%d/%y') #grabbing the first upcoming meeting date
        meetingChangeSizes = changeDict[meetingDate][0] #grabs the list of binary rate changes for the first upcoming meeting
        meetingChangeProbs = changeDict[meetingDate][1] #grabs the list of the corresponding probabilites for the binary rate changes

        #Now we will create the dataframe for the first upcoming meeting
        cumulativeDf = pd.DataFrame([dict(zip(meetingChangeSizes, meetingChangeProbs))], index = [meetingDate])

        prevChangeSizes = meetingChangeSizes 
        prevChangeProbs = meetingChangeProbs 

        # Add subsequent meetings data by calculating cumulative hike sizes and probabilities
        for i in range(1, len(changeDict)):
            
            #We now do essentially the same thing we did above, we want to grab the list of binary rate changes and their corresponding probabilites for the next meeting
            meetingDate = dates[i].strftime('%m/%d/%y')
            currChangeSizes = changeDict[meetingDate][0]
            currChangeProbs = changeDict[meetingDate][1]


            size_list = np.add.outer(prevChangeSizes, currChangeSizes) #This creates a matrix of the linear combinations of the previous and current rate changes 
            #as we continue to move forward in time, the size list will be the linear combinations of the previous rate changes and the current rate changes
            prob_list = np.multiply.outer(prevChangeProbs, currChangeProbs) #This creates a matrix of the linear combinations of the previous and current probabilities
            
            #because np.add.outer and np.multiply.outer create a matrix, we need to flatten it to get a list of the linear combinations
            size_list_flat = size_list.flatten()
            prob_list_flat = prob_list.flatten()
            
            #we now want to merge any duplicate rate changes and add the probabilities togther (ex. there might be two ways to get to 50 bps cut in the next meet, 25 and 25 or 50 and 0)
            #ultamitely the cumulative probabilty of getting to a 50 bps cut in this meeting is the sum of the probabilities of the two ways to get to a 50 bps cut
            aggValues = {}
            for value, probability in zip(size_list_flat, prob_list_flat):
                aggValues[int(value)] = float(aggValues.get(value, 0)) + float(probability)

            meetingChangeSizes = list(aggValues.keys())
            meetingChangeProbs = list(aggValues.values())
                    
            # Add meeting data to the dataframe
            cumulativeDf = pd.concat([cumulativeDf, pd.DataFrame([dict(zip(meetingChangeSizes, meetingChangeProbs))], index = [meetingDate])]).fillna(0.0)
            
            # Update lead meeting info for the next round
            prevChangeSizes = meetingChangeSizes 
            prevChangeProbs = meetingChangeProbs
        
        cumulativeDf.index.name = 'Meeting Date'
        cumulativeDf = cumulativeDf.sort_index(axis=1)

        return cumulativeDf

    def FedWatch(self):
        #This function will convert our bps numbers, -25bps to actual fed funds rates
        cumulativeDf = self.cumulativeDistribution()
        changes = cumulativeDf.columns
        newcols = []
        for change in changes:
            leftBound = self.lowerLimit + float(change)/100
            rightBound = self.upperLimit + float(change)/100
            newcols.append(f"{leftBound} - {rightBound}")
        cumulativeDf.columns = newcols
        return cumulativeDf






