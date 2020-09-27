import os
import requests
import requests_cache
import pandas as pd

API_KEY = os.environ.get('NEWS_API')


class NewsClient:
    URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key=API_KEY):
        self._api_key = api_key
        self._headers = {"Content-Type": "Application/JSON",
                      "Authorization": self._api_key}

    def _get_json(self, query=None, keywords_title=None, **kwargs):
        requests_cache.install_cache("news_cache")
        payload = {
            'sources': 'bbc-news,the-verge',
            'domains': 'bbc.co.uk,techcrunch.com',
            'language': 'en'
        }

        if query and isinstance(query,str):
            payload['q'] = query
        if keywords_title:
            payload['qInTitle'] = keywords_title

        req = requests.get(self.URL, headers=self._headers, timeout=30, params=payload)
        return req.json()

    def get_news(self, query=None, keywords_title=None, as_dict=False,**kwargs):
        results = self._get_json(query, keywords_title, **kwargs)
        if as_dict:
            results = results.get('articles')
        else:
            results = pd.DataFrame(results['articles'])
            results['source'] = results['source'].apply(lambda x: x.get('name') if 'name' in x else x)
        return results


