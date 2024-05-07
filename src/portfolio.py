
from spot import Spot
from pair import Pair
from transaction import Transaction
from apptypes import Quotes

class Holding(Spot):
    quote: float
    value: float
    transactions: list[Transaction]

    def __init__(self, s: str, q: float = 0.0):
        super().__init__(s, q)
        self.quote = 0.0
        self.value = 0.0
        self.transactions = []

    def to_json(self):
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'quote': self.quote,
            'value': self.value,
            'transactions': self.transactions,
        }

    def add_transaction(self, transaction: Transaction):
        self.transactions.append(transaction)

class Portfolio():
    parent: 'Portfolio'
    name: str
    level: int
    symbols: set
    sell_symbols: set
    buy_symbols: set
    fees: dict[str, Spot]
    transactions: list[Transaction]
    transactions_c: int
    subs: list['Portfolio']
    pairs: dict[str, Pair]
    holdings: dict[str, Holding]

    def __init__(self, name: str, parent: 'Portfolio' = None):
        self.name = name
        if parent is not None:
            self.level = parent.level + 1
        else:
            self.level = 0
        self.parent = parent
        self.symbols = set()
        self.sell_symbols = set()
        self.buy_symbols = set()
        self.fees = {}
        self.transactions = []
        self.transactions_c = 0
        self.subs = []
        self.pairs = {}
        self.holdings = {}

    def to_json(self):
        return {
            'name': self.name,
            'pairs': self.pairs,
            'holdings': self.holdings,
            'fees': self.fees,
        }

    def add_portfolio(self, portfolio: 'Portfolio'):
        self.subs.append(portfolio)

    def add_transaction(self, transaction: Transaction):
        self.transactions.append(transaction)

        ppair = self.add_pair(transaction.pair, transaction.ttype)
        ppair.add_transaction(transaction)

        if transaction.fee is not None:
            self.add_fee(transaction.fee)

        self.transactions_c += 1
        self.sell_symbols.add(transaction.sell_symbol)
        self.buy_symbols.add(transaction.buy_symbol)

        if self.parent is not None:
            self.parent.add_transaction(transaction)

    def add_pair(self, tpair: Pair, ttype: str) -> Pair:
        # print(f'-> add_pair({self.name},{tpair},{ttype})')

        if tpair.name in self.pairs:
            ppair = self.pairs[tpair.name]
        else:
            ppair = Pair(tpair.name)
            ppair.sell_spot = Spot(tpair.sell_spot.symbol)
            ppair.buy_spot = Spot(tpair.buy_spot.symbol)

            self.pairs[ppair.name] = ppair

        if ttype == 'buy':
            ppair.add_buy(tpair)
        elif ttype == 'sell':
            ppair.add_sell(tpair)

        return ppair

    def add_fee(self, fee: Spot):
        print(f'-> add_fee({self.name}, {fee})')

        if fee.symbol in self.fees:
            pfee = self.fees[fee.symbol]
        else:
            pfee = Spot(s=fee.symbol)
            self.fees[fee.symbol] = pfee

        pfee.add_spot(fee)

    def calc(self):
        self.holdings = {}
        for pair_id, pair in self.pairs.items():

            if pair.sell_spot.symbol not in self.holdings:
                holding = Holding(pair.sell_spot.symbol)
                holding.transactions = pair.transactions

                self.holdings[pair.sell_spot.symbol] = holding

            if pair.buy_spot.symbol not in self.holdings:
                holding = Holding(pair.buy_spot.symbol)
                holding.transactions = pair.transactions

                self.holdings[pair.buy_spot.symbol] = holding

        for sym, holding in self.holdings.items():
            for pair_id, pair in self.pairs.items():
                if sym == pair.sell_spot.symbol:
                    holding.sub_spot(pair.sell_spot)
                elif sym == pair.buy_spot.symbol:
                    holding.add_spot(pair.buy_spot)

        for sub_portfolio in self.subs:
            sub_portfolio.calc()

    def quotes(self, quotes: Quotes, convert: str):
        for transaction in self.transactions:
            print(f'-> calc trx: {transaction}')

            pair = transaction.pair

            if pair.sell_spot.symbol == convert:
                print(f'-> sell spot')
                pair.buy_spot.value = quotes[pair.buy_spot.symbol] * pair.buy_spot.quantity
                pair.buy_spot.profit = pair.buy_spot.value - pair.sell_spot.quantity
            elif pair.buy_spot.symbol == convert:
                print(f'-> buy spot')
                raise NotImplementedError()
                pair.sell_spot.value = quotes[pair.sell_spot.symbol] * pair.sell_spot.quantity
                pair.sell_spot.profit = 42

        for sym, spot in self.holdings.items():
            if spot.symbol in quotes:
                quote = quotes[spot.symbol]
                spot.quote = quote
                spot.value = quote * spot.quantity

        self.fee_value = 0.0
        for fee_id, fee in self.fees.items():
            # print(f'-> calc fee: {fee}')

            if fee.symbol == convert:
                self.fee_value += fee.quantity
            elif fee.symbol in quotes:
                self.fee_value += fee.quantity * quotes[fee.symbol]

        # print(f'-> self.fee_value={self.fee_value}')

        for sub_portfolio in self.subs:
            sub_portfolio.quotes(quotes, convert)
