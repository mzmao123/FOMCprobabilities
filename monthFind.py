
import pandas as pd
import math
from datetime import datetime as dt
from calendar import monthrange
from dateutil.relativedelta import relativedelta as rd
#import holidays

class FOMCfinder:
    def __init__(self, targetDate: dt, fomcDates: list, numProjections: int):
        self.targetDate = targetDate
        self.fomcDates = fomcDates
        self.fomcDates = sorted(self.fomcDates)
        self.numberProjections = numProjections
        
    
    def findMeetingBounds(self) -> dt:
        # here we will find the left and right bounds of the meeting dates: i.e the nearest past and future meeting dates
        # we first convert our fomcdates so that they are in string form to compare to our targetDate
        targetDateLeft = str(self.targetDate.strftime('%y/%m'))
        nearestLeftEmptyMonth = None
        fomcDatesLeft = [date.strftime('%y/%m') for date in self.fomcDates if date.strftime('%y/%m') <= targetDateLeft]
            # this gives us the FOMC meetings that are to the left of our targetDate
            
        earliestFOMC = sorted(fomcDatesLeft)[0]

        while targetDateLeft >= earliestFOMC: #fomcDatesLeft is sorted in ascending order
            if targetDateLeft not in fomcDatesLeft:
                nearestLeftEmptyMonth = targetDateLeft
                break
            else:
                targetDateLeft = (dt.strptime(targetDateLeft, '%y/%m') - rd(months=1)).strftime('%y/%m')
        if nearestLeftEmptyMonth == None:
            return ValueError("No starting empty month found")

        # now we will find the right bound
        #here it gets a little bit trickier because, in our main code we want to be able to work back from our the number of meetings we want to project
        numMeetings = 0 # we will use this counter to find the last month without a meeting after our numProjections fomc meetings
        targetDateRight = self.targetDate.strftime('%y/%m')
        nearestRightEmptyMonth = None
        fomcDatesRight = [date.strftime('%y/%m') for date in self.fomcDates if date.strftime('%y/%m') >= targetDateRight]
        lastFOMC = fomcDatesRight[-1]
        while targetDateRight <= lastFOMC: 
            if targetDateRight in fomcDatesRight:
                numMeetings += 1
            else:
                nearestRightEmptyMonth = targetDateRight
                if numMeetings >= self.numberProjections:
                    break
            targetDateRight = (dt.strptime(targetDateRight, '%y/%m') + rd(months=1)).strftime('%y/%m')
        if nearestRightEmptyMonth == None:
            return ValueError("No ending empty month found")
        if numMeetings < self.numberProjections:
            return ValueError("Not enough meetings found")

        return (dt.strptime(nearestLeftEmptyMonth, '%y/%m').strftime('%m/%y'), dt.strptime(nearestRightEmptyMonth, '%y/%m').strftime('%m/%y'))
    
    def createFOMCDataFrame(self) -> pd.DataFrame:
        #Here we will create a dataframe with all the information needed for our projection (month, meeting or no meeting, ticker, and order)
        startMonth, endMonth = self.findMeetingBounds()
    
        #First we will create a list containing all the months between the start and end months
        months = []
        currentMonth = dt.strptime(startMonth, '%m/%y')
        endMonth = dt.strptime(endMonth, '%m/%y')

        while currentMonth <= endMonth:
            months.append(currentMonth.strftime("%m/%y"))
            currentMonth = (currentMonth + rd(months=1))
        
        #We will now create a list of all the contract tickers for each month
        monthCodes ={'january':'F','february':'G','march':'H','april':'J',
        'may':'K','june':'M','july':'N','august':'Q','september':'U',
        'october':'V','november':'X','december':'Z'}

        monthDict = {1:"january",2:"february",3:"march",4:"april",5:"may",6:"june",7:"july",8:"august",
        9:"september",10:"october",11:"november",12:"december"}

        tickers = []
        for month in months:
            year = month.split('/')[1][-2:]
            month = int(month.split('/')[0])
            code = monthCodes[monthDict[month]]
            ticker = "ZQ" + code + str(year) + ".F"
            tickers.append(ticker.lower())
            
        fomcMeetings = self.fomcDates

        fomcYN = [] 

        for date in months:
            flag = False
            for meeting in fomcMeetings:
                if meeting.strftime('%m/%y') == date:
                    fomcYN.append(meeting.strftime('%m/%d/%y'))
                    flag = True
                    break
            if flag == False:
                fomcYN.append("No Meeting")
        #We will now create a list of the meeting dates or no meeting dates for each month, we have to do this so that 

        targetYear, targetMonth = self.targetDate.year, self.targetDate.month
        positionIndex = None
        for index, month in enumerate(months):
            if month == f"{targetMonth:02d}/{targetYear % 100:2d}":
                positionIndex = index
                break
        if positionIndex == None:
            return ValueError("Target date not found in months list")
        
        if fomcYN[positionIndex] == "No Meeting" or dt.strptime(fomcYN[positionIndex], '%m/%d/%y') <= self.targetDate:
            leftPointer = positionIndex 
            rightPointer = positionIndex +1
        else:
            leftPointer = positionIndex - 1
            rightPointer = positionIndex 

        orderList = []
        backCounter = - 1

        while leftPointer >= 0:

            if fomcYN[leftPointer] == "No Meeting":
                orderList.insert(0, 0)
            else:
                orderList.insert(0, backCounter)
                backCounter -= 1
            leftPointer -= 1

        forwardCounter = 1

        while rightPointer < len(months):
            if fomcYN[rightPointer] == "No Meeting":
                orderList.append(0)
            else:
                orderList.append(forwardCounter)
                forwardCounter += 1

            rightPointer += 1

        fullFrame = pd.DataFrame({
            "Date (MM/YY)": months,
            "Ticker": tickers,
            "Meeting Date": fomcYN,
            "Order": orderList

        })

        return fullFrame
