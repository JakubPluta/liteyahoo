from liteyahoo.news_scrapers.finviz import FinVizScraper
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import pandas as pd


class Sentiment:
    def __init__(self, symbol):
        self._symbol = symbol
        self._news_clients = FinVizScraper()
        self._vader = SentimentIntensityAnalyzer()
        self._stats = {}
        if isinstance(symbol,str):
         self._news = self._news_clients.scrape(symbol)

    def _analyze(self):
        scores = self._news['Header'].apply(self._vader.polarity_scores).tolist()
        scores_df = pd.DataFrame(scores)
        scores_df = self._news[['Symbol','Time','Header']].join(scores_df)
        return scores_df.groupby(['Symbol']).mean()

    @property
    def sentiment_info(self):
        sentiment = self._analyze()
        if sentiment.get('compound')[0] < 0:
            sent_desc = "Negative"
        else:
            sent_desc = "Positive"

        return {
            "Symbol" : self._symbol,
            "Score" : sentiment.get('compound')[0],
            "Sentiment" : sent_desc
        }

