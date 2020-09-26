from .client import Client


class Stock(Client):
    def __init__(self,symbol):
        super().__init__(symbol)

        if not self._fundamentals:
            self.fundamentals()

    @property
    def cash_flow(self):
        return self._cash_flow

    @property
    def balance_sheet(self):
        return self._balance_sheet

    @property
    def income_statement(self):
        return self._income_statement

    @property
    def recommendations(self):
        return self._recommendations

    @property
    def splits(self):
        return self._splits

    @property
    def dividends(self):
        return self._dividends

    @property
    def trends(self):
        return self._trends

    @property
    def events(self):
        return self._events

    @property
    def major_holders(self):
        return self._holders.get('major_holders')

    @property
    def insider_holders(self):
        return self._holders.get('insider_holders')

    @property
    def summary(self):
        return self._company_info.get('summary')

    @property
    def fund_owner(self):
        return self._company_info.get('fund_owner')

    @property
    def insider_transactions(self):
        return self._company_info.get('insider_transactions')

    @property
    def prices(self):
        return self._company_info.get('prices')

    @property
    def sustainability(self):
        return self._company_info.get('sustainability')