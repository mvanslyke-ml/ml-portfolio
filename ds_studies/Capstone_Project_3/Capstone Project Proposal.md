### CAPSTONE PROJECT 3:
### A TIME SERIES PREDICTOR FOR STOCK MARKET VALUES
***

#### PROBLEM STATEMENT FORMATION: 
Train a time series model which predicts stock prices with an %85 - %95 accuracy by April 10, 2024 as a piece for a larger model, ultimately directed towards automating ideal trading actions depending on pre-defined investing goals.

#### CONTEXT:
The stock market since its renowned inception by the East India trading Co. well back into the colonial era, has become a remarkable powerhouse of investment and wealth building; beneficial to both private investors as well as the businesses whose shares are being traded and valued. The terrible downside of this is the associated risk, caused by market forces and dare I say human whimsy?  With that said though, there are a multitude of factors used to determine risk, one of which is market trend: Is the stock value rising or falling in short.

#### CRITERIA FOR SUCCESS:
As a piece of a much larger project in the long term, we will endeaver to achieve the best reasonable accuracy and precision possible with this model, between %85-%95 at least, for proof of concept, in predicting stock market values. Measuered most likely using MSE, RMSE values for the average distance between predicted and true values.

#### SCOPE OF SOLUTION SPACE:
This will be a general application model which SOLELY predicts future prices derived from previous price points in the Time Series.  We will look for improving upon this prediction by taking into account predictions from other models and factors in order to make the best prediction possible but this as stated before is the long-term goal. This project will ONLY focus on the Time Series data.

#### CONSTRAINTS:
We will need to worry a lot about noise as the the stock market is a very noisy place.  We will need to take great care in preparing and transforming our data to give the model the best odds of success possible within reason. Since we will only be focused on Time Series, we will be limiting our selves to the variations of ARIMA models and LSTMs.

#### STAKEHOLDERS:
A short list of stakeholders:
- Investors
- Entrepeneurs
- CEO's
- Private Investors
- Finanacial Advisors
- Portfolio Managers
- Financial Security
- Risk Management
- Etc.

#### DATA SOURCES:
We will pull data from the various stock market API's:
- NASDAQ
- Quandl
- OpenFin
- MarketStack
- FinnHub
- Polygon
- https://www.kaggle.com/datasets/finnhub/sp-500-futures-tick-data-sp