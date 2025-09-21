# FOMCprobabilities
Calculating market implied odds of FOMC actions. This project is heavily inspired by the CME FedWatch tool and uses many of the same methods described in their [methodolgy paper][https://www.cmegroup.com/articles/2023/understanding-the-cme-group-fedwatch-tool-methodology.html].

To use it please launch the FedWatch function by initializing an object with the current date, a list containging upcoming FOMC meetings, how many meetings you want to project, and the current bounds for the target FFR.
The method currently only works for the current date simply due to limitations on gathering historical FFR futures data. 

I am currently working on buiding a similar tool using SFOR option implied probabilities instead of using Fed Funds Rate Futures, just because SOFR is more liquid and also would allow for more than just binary information on the upcoming meeting. (When using the CME method, we are limited to only 2 possible outcomes for the upcoming meeting, where as an option implied probability distribution can have >2).
