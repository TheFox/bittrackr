
from apptypes import ConvertSymbols
from json_helper import ComplexEncoder
from json import dumps
from spot import Spot
from pair import Pair
from transaction import Transaction
from holding import Holding
from quotes import Quotes

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
    spots: dict[str, Spot]
    holdings: dict[str, Holding]
    cost: Spot|None

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
        self.fee_value = 0.0
        self.transactions = []
        self.transactions_c = 0
        self.subs = []
        self.pairs = {}
        self.spots = {}
        self.holdings = {}
        self.cost = None

    def to_json(self):
        return {
            'name': self.name,
            'pairs': self.pairs,
            'holdings': self.holdings,
            'fees': self.fees,
            'fee_value': self.fee_value,
            'spots': self.spots,
        }

    def add_portfolio(self, portfolio: 'Portfolio'):
        self.subs.append(portfolio)

    def add_transaction(self, transaction: Transaction):
        if self.parent is not None:
            self.parent.add_transaction(transaction)

        self.transactions.append(transaction)
        self.transactions_c += 1

        if transaction.fee is not None:
            self.add_fee(transaction.fee)

        # print(f'-> add trx: {transaction}')
        if transaction.is_pair:
            ppair = self.add_pair(transaction.pair, transaction.ttype)
            ppair.add_transaction(transaction)

            self.sell_symbols.add(transaction.sell_symbol)
            self.buy_symbols.add(transaction.buy_symbol)
        else:
            if transaction.spot.symbol in self.spots:
                spot = self.spots[transaction.spot.symbol]
            else:
                spot = Spot(s=transaction.spot.symbol)
                self.spots[transaction.spot.symbol] = spot

            spot.add_trx_count()

            if transaction.ttype == 'in':
                spot.add_spot(transaction.spot)
            elif transaction.ttype == 'out':
                spot.sub_spot(transaction.spot)
            else:
                raise ValueError(f'Unknown Transaction type: {transaction.ttype}')

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
        else:
            raise ValueError(f'Unknown Transaction type: {ttype}')

        return ppair

    def add_fee(self, fee: Spot):
        if fee.symbol in self.fees:
            pfee = self.fees[fee.symbol]
        else:
            pfee = Spot(s=fee.symbol)
            self.fees[fee.symbol] = pfee

        pfee.add_spot(fee)

    def calc(self, convert: str):
        for sub_portfolio in self.subs:
            sub_portfolio.calc()

        self.holdings = {}
        for pair_id, pair in self.pairs.items():
            # print(f'-> create holdings from pairs {pair}')

            trx_count = len(pair.transactions)

            if pair.sell_spot.symbol not in self.holdings:
                self.holdings[pair.sell_spot.symbol] = Holding(pair.sell_spot.symbol)
            self.holdings[pair.sell_spot.symbol].add_trx_count(trx_count)

            if pair.buy_spot.symbol not in self.holdings:
                self.holdings[pair.buy_spot.symbol] = Holding(pair.buy_spot.symbol)
            self.holdings[pair.buy_spot.symbol].add_trx_count(trx_count)

        for sym, spot in self.spots.items():
            # print(f'-> create holdings from spots {spot}')

            if spot.symbol not in self.holdings:
                self.holdings[spot.symbol] = Holding(spot.symbol)
            self.holdings[spot.symbol].add_trx_count(spot.trx_count)

        # TODO
        #for fee_id, fee in self.fees.items():

        for hsym, holding in self.holdings.items():
            # print(f'-> calc holding: {holding}')

            if convert == holding.symbol:
                self.cost = Spot(s=holding.symbol)
                self.cost.quantity = holding.quantity * -1

            for pair_id, pair in self.pairs.items():
                if hsym == pair.sell_spot.symbol:
                    holding.sub_spot(pair.sell_spot)
                elif hsym == pair.buy_spot.symbol:
                    holding.add_spot(pair.buy_spot)

            for ssym, spot in self.spots.items():
                if ssym == hsym:
                    holding.add_spot(spot)

    def get_convert_symbols(self, convert: str) -> ConvertSymbols:
        symbols = {}

        def add(sym: str, val: str):
            if sym not in symbols:
                symbols[sym] = []
            if val not in symbols[sym]:
                symbols[sym].append(val)

        # Pairs
        for pair_id, pair in self.pairs.items():
            # print(f'-> pair {pair}')

            if pair.sell_spot.symbol != convert and pair.buy_spot.symbol != convert:
                add(pair.sell_spot.symbol, pair.buy_spot.symbol)

            elif pair.sell_spot.symbol == convert:
                add(pair.sell_spot.symbol, pair.buy_spot.symbol)

            elif pair.buy_spot.symbol == convert:
                add(pair.buy_spot.symbol, pair.sell_spot.symbol)

        # Spots
        for ssym, spot in self.spots.items():
            # print(f'-> spot: {ssym} {spot}')
            add(convert, spot.symbol)

        # Holdings
        for hsym, holding in self.holdings.items():
            if holding.symbol == convert:
                continue
            # print(f'-> quotes holding: {holding}')
            add(convert, holding.symbol)

        # Fees
        for fee_id, fee in self.fees.items():
            if fee.symbol == convert:
                continue
            # print(f'-> fee {fee_id} {fee}')
            add(convert, fee.symbol)

        return symbols

    def quotes(self, quotes: Quotes, convert: str):
        # print(f'-> quotes: {quotes}')
        # print(f'-> ck convert: {convert}')

        for sub_portfolio in self.subs:
            sub_portfolio.quotes(quotes, convert)

        for transaction in self.transactions:

            if transaction.is_pair:
                # print(f'-> calc pair trx: {transaction}')
                # print()

                pair = transaction.pair

                # print(f'->    ck sell->buy: {pair.sell_spot.symbol}->{pair.buy_spot.symbol}')

                transaction.cprice = quotes.get(convert, pair.buy_spot.symbol)

                if pair.sell_spot.symbol == convert:
                    cquote = quotes.get(convert, pair.buy_spot.symbol)
                    pair.value = cquote * pair.buy_spot.quantity
                    pair.profit = pair.value - pair.sell_spot.quantity

                    # print(f'->    ck cquote: {cquote}')
                    # print(f'->    ck value: {pair.value}')
                    # print(f'->    ck profit: {pair.profit}')
                elif pair.buy_spot.symbol == convert:
                    raise NotImplementedError()
                else:  # elif pair.sell_spot.symbol != convert and pair.buy_spot.symbol == convert:
                    squote = quotes.get(convert, pair.sell_spot.symbol)
                    bquote = quotes.get(convert, pair.buy_spot.symbol)

                    svalue = squote * pair.sell_spot.quantity
                    bvalue = bquote * pair.buy_spot.quantity
                    #pair.profit = svalue - bvalue
                    pair.profit = bvalue - svalue

                    # print(f'->    ck svalue {pair.sell_spot.symbol}: {svalue} ({pair.sell_spot.quantity})')
                    # print(f'->    ck bvalue  {pair.buy_spot.symbol}: {bvalue} ({pair.buy_spot.quantity})')
                    # print(f'->    ck profit: {pair.profit}')

                    pair.value = bvalue

            else:
                spot = transaction.spot
                #transaction.price = 1
                #transaction.cprice = quotes.get(convert, pair.buy_spot.symbol)
                quote = quotes.get(convert, spot.symbol)
                spot.value = quote * spot.quantity
                spot.profit = spot.value
                spot.price = quote

                if transaction.ttype == 'in':
                    pass
                elif transaction.ttype == 'out':
                    spot.profit *= -1
                else:
                    raise ValueError(f'Unknown Transaction type: {transaction.ttype}')

        # print('------- transactions -------')
        # print(dumps(self.transactions, indent=2, cls=ComplexEncoder))
        # print('------------------------')

        # print('------- holdings A -------')
        # print(dumps(self.holdings, indent=2, cls=ComplexEncoder))
        # print('------------------------')

        # Holdings
        for hsym, holding in self.holdings.items():
            if holding.symbol == convert:
                continue
            # print(f'-> quotes holding: {holding}')
            quote = quotes.get(convert, holding.symbol)

            holding.quote = quote
            holding.value = quote * holding.quantity

        # print('------- holdings B -------')
        # print(dumps(self.holdings, indent=2, cls=ComplexEncoder))
        # print('------------------------')

        # Fees
        for fee_id, fee in self.fees.items():

            if fee.symbol == convert:
                # print(f'-> fee A {fee}')
                self.fee_value += fee.quantity
            else:
                quote = quotes.get(convert, fee.symbol)
                self.fee_value += quote * fee.quantity
                # print(f'-> fee B {fee} quote={quote}')
