import pandas as pd
from bs4 import BeautifulSoup
import requests


class Fidelity:
    BASE = 'https://eresearch.fidelity.com/eresearch/evaluate/news/basicNews.jhtml?symbols='
    ROOT = 'https://eresearch.fidelity.com'

    def __init__(self):
        self._data = {}

    def scrape(self, symbol, as_dict=False, detailed=False):
        req = requests.get(self.BASE + symbol)
        page = req.text
        soup = BeautifulSoup(page, 'lxml')
        links = soup.find_all(name="li", attrs={'class': "news-item"})

        titles = []
        articles = []

        for link in links:
            href = self.ROOT + link.h3.a['href']
            title = link.p.text.strip()
            titles.append(title)
            if detailed:
                req = requests.get(href)
                page = req.text
                soup = BeautifulSoup(page, 'lxml')
                article = soup.find(id='articleContainer').text.strip()
                articles.append(article)

                self._data[symbol] = {
                        'Symbol' : symbol,
                        'Title': titles,
                        'Article': articles
                    }
            else:
                self._data[symbol] = {
                        'Symbol' : symbol,
                        'Header': titles,
                }

        if as_dict:
            return self._data[symbol]
        else:
            return pd.DataFrame(self._data[symbol])

