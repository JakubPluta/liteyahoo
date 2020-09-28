from abc import ABC, abstractmethod, abstractclassmethod


class NewsScraper:

    def __init__(self, base_url, headers=None):
        self.BASE = base_url
        self.HEADERS = headers
        self._data = {}

    @abstractmethod
    def scrape(self):
        raise NotImplementedError


