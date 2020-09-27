import pandas as pd
from bs4 import BeautifulSoup
import requests
import requests_cache
from nltk.sentiment.vader import SentimentIntensityAnalyzer


class FinVizScraper:
    BASE = 'https://finviz.com/quote.ashx?t='
    HEADERS = {'user-agent': 'my-app/0.0.1'}

    def __init__(self):
        self._data = {}

    def scrape(self, symbol, as_dict = False):
        req = requests.get(self.BASE + symbol, headers=self.HEADERS)
        page = req.text
        soup = BeautifulSoup(page, 'lxml')
        news = soup.find(id='news-table')
        table = news.find_all('tr')

        self._data[symbol] = {
            'Symbol' : symbol,
            'Time' : [item.td.text.strip() for item in table],
            'Header' : [item.a.text for item in table],
            'Url' : [item.a.get('href') for item in table]
        }

        if as_dict:
            return self._data[symbol]
        else:
            return pd.DataFrame(self._data[symbol])

