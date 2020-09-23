import time as t
import datetime as dt
import requests as req
import pandas as pd
import numpy as np
import json
import re
from .utils import convert_to_timestamp, proxy_setter


class Client:

    URL = 'https://query1.finance.yahoo.com'
    START_DATE = "1971-01-01"

    def __init__(self, symbol: str):
        self._symbol = symbol
        self._company_info: json = None
        self._historical_prices: json = None
        self._recommendations: json = None
        self._fundamentals: json = None
        self._cash_flow: json = None
        self._income_statement: json = None
        self._balance_sheet: json = None
        self._splits: pd.DataFrame() = None
        self._dividends: pd.DataFrame() = None

        self._financials: json = None

        self._sentiment: json = None

    def historical_prices(self, period="1y", interval="1d", start=None,
                          end=None, proxy=None, **kwargs):

        params = {}
        if period in [None, False, 0, 'max'] or not start:
            if not start:
                start = convert_to_timestamp(self.START_DATE)
            if not end:
                end = convert_to_timestamp(dt.datetime.now())
            params["period1"], params["period2"] = start, end
        else:
            params["range"] = period.lower()

        params["interval"] = interval.lower()
        params["events"] = "div,splits"

        if proxy: proxy = proxy_setter(proxy)

        url = f"{self.URL}/v8/finance/chart/{self._symbol}"
        data = req.get(url=url, params=params, proxies=proxy)

        if "Will be right back" in data.text:
            raise RuntimeError("Yahoo down")

        data = data.json()

        quotes = {}

        if 'chart' in data:
            pre_quotes = data['chart']['result'][0]
            indicators = pre_quotes['indicators']["quote"][0]
            quotes['timestamp'] = pre_quotes['timestamp']
            quotes['volume'] = indicators["volume"]
            quotes['open'] = indicators['open']
            quotes['close'] = indicators['open']
            quotes['high'] = indicators['open']
            quotes['low'] = indicators['open']

        else:
            raise KeyError("No quotes found")

        quotes['index'] = self.timestamp_converter(quotes['timestamp'])

        quotes_df = pd.DataFrame.from_dict(quotes).set_index('index').drop('timestamp',axis=1)
        self._historical_prices = quotes_df[['open', 'high', 'low', 'close', 'volume']]

        if "events" in pre_quotes:
            if "dividends" in pre_quotes["events"]:
                dividends_df = pd.DataFrame(list(pre_quotes['events']['dividends'].values()))
                dividends_df['date'] = pd.to_datetime(dividends_df['date'],unit='s')
                dividends_df.set_index('date', inplace=True)
                self._dividends = dividends_df

            if 'splits' in pre_quotes["events"]:
                splits_df = pd.DataFrame(list(pre_quotes['events']['splits'].values()))[['date','splitRatio']]
                splits_df['date'] = pd.to_datetime(splits_df['date'], unit='s')
                splits_df.set_index('date',inplace=True)
                self._splits = splits_df

        return quotes_df

    @staticmethod
    def timestamp_converter(timestamp):
        return [dt.datetime.fromtimestamp(_) for _ in timestamp]













