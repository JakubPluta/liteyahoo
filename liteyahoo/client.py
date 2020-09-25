import time as t
import datetime as dt
import requests as req
import pandas as pd
import numpy as np
import json
import re
from .utils import convert_to_timestamp, proxy_setter
from json import JSONDecodeError
import requests_cache


class Client:

    URL = 'https://query1.finance.yahoo.com'
    URL_TO_SCRAPE = 'https://finance.yahoo.com/quote'

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
        quotes_df.dropna(inplace=True)
        self._historical_prices = quotes_df[['open', 'high', 'low', 'close', 'volume']]

        if "events" in pre_quotes:
            if "dividends" in pre_quotes["events"]:
                dividends_df = pd.DataFrame(list(pre_quotes['events']['dividends'].values()))
                dividends_df['date'] = pd.to_datetime(dividends_df['date'], unit='s')
                dividends_df.set_index('date', inplace=True)

            if 'splits' in pre_quotes["events"]:
                splits_df = pd.DataFrame(list(pre_quotes['events']['splits'].values()))[['date','splitRatio']]
                splits_df['date'] = pd.to_datetime(splits_df['date'], unit='s')
                splits_df.set_index('date',inplace=True)
                quotes_df = pd.concat([quotes_df,splits_df], axis=1, sort=True)

        return quotes_df

    def fundamentals(self, element=None, proxy=None, **kwargs):
        """
        * Finance
        """
        data = self._scrape_data_to_json(proxy, endpoint='/financials')

        # CashFlow
        cash_flow = data.get('cashflowStatementHistory')['cashflowStatements']
        cash_flow_quarterly = data.get('cashflowStatementHistoryQuarterly')['cashflowStatements']
        cash_flow_df = self._create_data_frame(cash_flow)
        cash_flow_quarterly_df = self._create_data_frame(cash_flow_quarterly)
        self._cash_flow = cash_flow_df

        # Balance Sheet
        balance_sheet = data.get('balanceSheetHistory')['balanceSheetStatements']
        balance_sheet_quarterly = data.get('balanceSheetHistoryQuarterly')['balanceSheetStatements']
        balance_sheet_df = self._create_data_frame(balance_sheet)
        balance_sheet_quarterly_df = self._create_data_frame(balance_sheet_quarterly)
        self._balance_sheet = balance_sheet_df

        # Income Statement
        income_statement = data.get('incomeStatementHistory')['incomeStatementHistory']
        income_statement_quarterly = data.get('incomeStatementHistoryQuarterly')['incomeStatementHistory']
        income_statement_df = self._create_data_frame(income_statement)
        income_statement_quarterly_df = self._create_data_frame(income_statement_quarterly)
        self._income_statement = income_statement_df



        # Holders

        data = self._scrape_data_to_json(proxy, endpoint='/holders')

        major_holders = data.get('majorDirectHolders')
        if 'holders' in major_holders:
            major_holders = pd.DataFrame(major_holders['holders'])

        insider_holders = data.get('insiderHolders')
        if 'holders' in insider_holders:
            try:
                insider_holders = pd.DataFrame(insider_holders['holders']).drop('maxAge',axis=1)[['name','relation','transactionDescription','latestTransDate']]
                insider_holders['latestTransDate'] = insider_holders['latestTransDate'].apply(lambda x: x.get('raw'))
                insider_holders['latestTransDate'] = pd.to_datetime(insider_holders['latestTransDate'],unit='s')
                insider_holders.set_index('latestTransDate',inplace=True)
            except KeyError:
                insider_holders = pd.DataFrame(insider_holders['holders']).drop('maxAge',axis=1)


        summary_detail = pd.DataFrame(data.get('summaryDetail')).T['raw']

        quote_type = pd.DataFrame(data.get('quoteType').items())

        fund_owner = pd.DataFrame(data.get('fundOwnership')['ownershipList'])

        fund_owner.drop('maxAge', axis=1,inplace=True)
        for col in fund_owner.columns:
            print(fund_owner[col])
            fund_owner[col] = fund_owner[col].apply(lambda x: x.get('raw') if isinstance(x,dict) else x)
        fund_owner['reportDate'] = pd.to_datetime(fund_owner['reportDate'], unit='s')
        fund_owner.set_index('reportDate', inplace=True)

        insider_transactions = data.get('insiderTransactions')
        if 'transactions' in insider_transactions:
            try:
                insider_transactions = pd.DataFrame(data.get('insiderTransactions')['transactions'])
                insider_transactions = insider_transactions[['filerName', 'transactionText', 'ownership',
                                                             'startDate', 'value', 'filerRelation', 'shares']]
                for col in ['startDate','value','shares']:
                    insider_transactions[col] = insider_transactions[col].apply(lambda x: x.get('raw') if isinstance(x,dict) else x)

                insider_transactions['startDate'] = pd.to_datetime(insider_transactions['reportDate'], unit='s')
                insider_transactions.set_index('startDate', inplace=True)

            except KeyError:
                insider_transactions = pd.DataFrame(data.get('insiderTransactions'))


    @staticmethod
    def _create_data_frame(data):
        df = pd.DataFrame(data).drop('maxAge',axis=1)
        for col in df.columns:
            df[col] = df[col].apply(lambda x: x.get('raw') if x not in [np.NaN, np.NAN, None, 'nan'] else None)
        if 'endDate' in df.columns:
            df['endDate'] = pd.to_datetime(df['endDate'],unit='s')
            df = df.set_index('endDate')
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













