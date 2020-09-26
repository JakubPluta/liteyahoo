import time as t
import datetime as dt
import requests as req
import pandas as pd
import numpy as np
import json
import re
from .utils import convert_to_timestamp, proxy_setter, parse_item
from json import JSONDecodeError
import requests_cache


class Client:

    URL = 'https://query1.finance.yahoo.com'
    URL_TO_SCRAPE = 'https://finance.yahoo.com/quote'

    START_DATE = "1971-01-01"

    def __init__(self, symbol: str):
        self._symbol = symbol
        self._company_info: dict = {}
        self._historical_prices: pd.DataFrame
        self._recommendations: json = None
        self._fundamentals = False
        self._cash_flow: json = None
        self._income_statement: json = None
        self._balance_sheet: json = None
        self._splits: pd.DataFrame() = None
        self._dividends: pd.DataFrame() = None
        self._trends = {}
        self._financials = None
        self._holders = {}
        self._events = None
        self._sentiment = None

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
        quotes_df.dropna(inplace=True)
        self._historical_prices = quotes_df[['open', 'high', 'low', 'close', 'volume']]

        if "events" in pre_quotes:
            if "dividends" in pre_quotes["events"]:
                dividends_df = pd.DataFrame(list(pre_quotes['events']['dividends'].values()))
                dividends_df['date'] = pd.to_datetime(dividends_df['date'], unit='s')
                dividends_df.set_index('date', inplace=True)
                self._dividends = dividends_df

            if 'splits' in pre_quotes["events"]:
                splits_df = pd.DataFrame(list(pre_quotes['events']['splits'].values()))[['date','splitRatio']]
                splits_df['date'] = pd.to_datetime(splits_df['date'], unit='s')
                splits_df.set_index('date',inplace=True)
                self._splits = splits_df

    def fundamentals(self, proxy=None, **kwargs):

        data = self._scrape_data_to_json(proxy, endpoint='/financials')

        # CashFlow
        cash_flow = data.get('cashflowStatementHistory')['cashflowStatements']
        cash_flow_quarterly = data.get('cashflowStatementHistoryQuarterly')['cashflowStatements']
        cash_flow_df = self._create_data_frame(cash_flow, date_col='endDate')
        cash_flow_quarterly_df = self._create_data_frame(cash_flow_quarterly, date_col='endDate')
        self._cash_flow = cash_flow_df

        # Balance Sheet
        balance_sheet = data.get('balanceSheetHistory')['balanceSheetStatements']
        balance_sheet_quarterly = data.get('balanceSheetHistoryQuarterly')['balanceSheetStatements']
        balance_sheet_df = self._create_data_frame(balance_sheet, date_col='endDate')
        balance_sheet_quarterly_df = self._create_data_frame(balance_sheet_quarterly, date_col='endDate')
        self._balance_sheet = balance_sheet_df

        # Income Statement
        income_statement = data.get('incomeStatementHistory')['incomeStatementHistory']
        income_statement_quarterly = data.get('incomeStatementHistoryQuarterly')['incomeStatementHistory']
        income_statement_df = self._create_data_frame(income_statement, date_col='endDate')
        income_statement_quarterly_df = self._create_data_frame(income_statement_quarterly,date_col='endDate')
        self._income_statement = income_statement_df

        # Holders
        data = self._scrape_data_to_json(proxy, endpoint='/holders')

        major_holders = data.get('majorDirectHolders')
        if 'holders' in major_holders:
            major_holders = self._create_data_frame(data=major_holders['holders'], date_col='latestTransDate').T

        self._holders['major_holders'] = major_holders

        insider_holders = data.get('insiderHolders')
        if 'holders' in insider_holders:
            insider_holders = self._create_data_frame(data=insider_holders['holders'],date_col='latestTransDate').T

        self._holders['insider_holders'] = insider_holders

        if 'summaryDetail' in data:
            self._company_info['summary'] = self._create_data_frame(data.get('summaryDetail'))['raw']

        if 'quote_type' in data:
            self._company_info['quote_type'] = self._create_data_frame(data.get('quoteType').items()).T

        if 'fundOwnership' in data:
            self._company_info['fund_owner'] = self._create_data_frame(data.get('fundOwnership')['ownershipList'],
                                                                       date_col='reportDate').T

        insider_transactions = data.get('insiderTransactions')
        if 'transactions' in insider_transactions:
            try:
                insider_transactions = pd.DataFrame(data.get('insiderTransactions')['transactions'])
                insider_transactions = insider_transactions[['filerName', 'transactionText', 'ownership',
                                                             'startDate', 'value', 'filerRelation', 'shares']]
                for col in ['startDate','value','shares']:
                    insider_transactions[col] = insider_transactions[col].apply(
                        lambda x: parse_item(x))
                insider_transactions['startDate'] = pd.to_datetime(insider_transactions['startDate'], unit='s')
                insider_transactions.set_index('startDate', inplace=True)
                self._company_info['insider_transactions'] = insider_transactions
            except KeyError:
                self._company_info['insider_transactions'] = pd.DataFrame(data.get('insiderTransactions'))

        if 'price' in data:
            try:
                prices = pd.DataFrame(data['price']).T
            except KeyError:
                prices = pd.DataFrame(data['price'])
            self._company_info['prices'] = prices.get('raw')

        # KEY STATS
        data = self._scrape_data_to_json(proxy, endpoint='/key-statistics')

        if 'defaultKeyStatistics' in data:
            self._key_stats = self._create_data_frame(data.get('defaultKeyStatistics')).get('raw')
        if 'calendarEvents' in data:
            self._events = self._create_data_frame(data.get('calendarEvents')).T
        if 'financialData' in data:
            self._financials =  self._create_data_frame(data.get('financialData')).get('raw')

        # Analysis
        data = self._scrape_data_to_json(proxy, endpoint='/analysis')
        self._trends['trend_recommendation'] = pd.DataFrame(data.get('recommendationTrend')['trend'])
        self._trends['index_recommendation'] = self._create_data_frame(data.get('indexTrend')['estimates']).T.dropna()
        self._trends['earnings_recommendation'] = self._create_data_frame(data.get('earningsTrend')['trend']).T.dropna()
        self._recommendations = self._create_data_frame(data=data.get('upgradeDowngradeHistory')['history'],date_col='epochGradeDate').T

        # sustainability
        data = self._scrape_data_to_json(proxy, endpoint='/sustainability')
        sustainability = {}
        if 'esgScores' in data:
            sus = data.get('esgScores')
            for item in sus:
                if isinstance(sus[item], dict):
                    sustainability[item] = sus[item]
        self._company_info['sustainability'] = pd.DataFrame(sustainability).T

        self._fundamentals = True

    @staticmethod
    def _create_data_frame(data, date_col=None):
        df = pd.DataFrame(data)
        if 'maxAge' in df.columns:
            df.drop('maxAge', axis=1, inplace=True)
        for col in df.columns:
            df[col] = df[col].apply(lambda x: parse_item(x))

        if date_col and date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col],unit='s')
            df = df.set_index(date_col)

        return df.T

    def _scrape_data_to_json(self, proxy, endpoint=""):
        if proxy: proxy = proxy_setter(proxy)

        url = f"{self.URL_TO_SCRAPE}/{self._symbol}" + endpoint
        requests_cache.install_cache("yahoo_cache")
        r = req.get(url=url, proxies=proxy)
        html = r.text

        if "QuoteSummaryStore" not in html:
            return {}

        try:
            html_split = html.split("root.App.main =")[1].split('(this)')[0].split(';\n}')[0].strip()
            json_data = json.loads(html_split)
            data = json_data['context']['dispatcher']['stores']['QuoteSummaryStore']
            return data

        except JSONDecodeError:
            return {}

    @staticmethod
    def timestamp_converter(timestamp):
        return [dt.datetime.fromtimestamp(_) for _ in timestamp]












