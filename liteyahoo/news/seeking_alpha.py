from bs4 import BeautifulSoup
import requests
import pandas as pd


class SeekingAlphaNews:
    BASE_URL = "https://seekingalpha.com"
    MARKET_NEWS_URL = 'https://seekingalpha.com/market-news'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (iPad; U; CPU OS 3_2_1 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Mobile/7B405'}

    def scrape(self):
        page = requests.get(self.MARKET_NEWS_URL, headers=self.HEADERS)
        soup = BeautifulSoup(page.text, features="lxml")
        news = soup.find(name="ul", attrs={'class':"item-list",'id':'latest-news-list'})

        id_list = [i.get('id') for i in news.find_all(name='li', attrs={'class':'item'})]
        id_list = [i.replace('latest-news-','')  for i in id_list if i]
        headings = [i.text for i in news.find_all('a')]
        urls = [self.BASE_URL+i['href'] for i in news.find_all('a')]
        date_list = [i.get('data-last-date') for i in news.find_all(name='li', attrs={'class':'item'})]
        date_list = [i.split()[0] for i in date_list if i]
        return pd.DataFrame({
            'Id' : id_list,
            'Date' : date_list,
            'Heading' : headings,
            'Url' : urls}
        )
