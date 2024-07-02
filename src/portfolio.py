
from logging import getLogger
from typing import Optional, cast
from apptypes import ConvertSymbols
from spot import Spot
from holding import Holding
from pair import Pair
from transaction import Transaction
from quotes import Quotes
from helper import sort_transactions

_logger = getLogger(f'app.{__name__}')

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
    costs: Optional[Spot]

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
        self.costs = None

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
        _logger.debug(f'add_transaction({self.name})')

        if self.parent is not None:
            self.parent.add_transaction(transaction)

        self.transactions.append(transaction)
        self.transactions_c += 1

        if transaction.fee is not None:
            self.add_fee(transaction.fee)

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
            spot.transactions.append(transaction)

            if transaction.ttype == 'in':
                spot.add_spot(transaction.spot)
            elif transaction.ttype == 'out':
                spot.sub_spot(transaction.spot)
            else:
                raise ValueError(f'Unknown Transaction type for add transaction to portfolio: {transaction.ttype}')

    def add_pair(self, tpair: Pair, ttype: str) -> Pair:
        _logger.debug(f'add_pair({self.name},{tpair},{ttype})')

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
        elif ttype == 'buy-order':
            pass
        elif ttype == 'sell-order':
            pass
        else:
            raise ValueError(f'Unknown Transaction type add pair to portfolio: {ttype}')

        return ppair

    def add_fee(self, fee: Spot):
        if fee.symbol in self.fees:
            pfee = self.fees[fee.symbol]
        else:
            pfee = Spot(s=fee.symbol)
            self.fees[fee.symbol] = pfee

        pfee.add_spot(fee)

    def calc(self):
        _logger.debug(f'calc({self.name})')

        for sub_portfolio in self.subs:
            sub_portfolio.calc()

        self.holdings = {}
        for pair_id, pair in self.pairs.items():
            trx_count = len(pair.transactions)

            if pair.sell_spot.symbol not in self.holdings:
                self.holdings[pair.sell_spot.symbol] = Holding(pair.sell_spot.symbol)

            self.holdings[pair.sell_spot.symbol].add_trx_count(trx_count)
            self.holdings[pair.sell_spot.symbol].transactions.extend(pair.transactions)

            if pair.buy_spot.symbol not in self.holdings:
                self.holdings[pair.buy_spot.symbol] = Holding(pair.buy_spot.symbol)

            self.holdings[pair.buy_spot.symbol].add_trx_count(trx_count)
            self.holdings[pair.buy_spot.symbol].transactions.extend(pair.transactions)

        for sym, spot in self.spots.items():
            if spot.symbol not in self.holdings:
                self.holdings[spot.symbol] = Holding(spot.symbol)

            self.holdings[spot.symbol].add_trx_count(spot.trx_count)
            self.holdings[spot.symbol].transactions.extend(spot.transactions)

        # TODO
        #for fee_id, fee in self.fees.items():

        for hsym, holding in self.holdings.items():

            for pair_id, pair in self.pairs.items():

                if holding.symbol == pair.sell_spot.symbol:
                    holding.sub_spot(pair.sell_spot)

                elif holding.symbol == pair.buy_spot.symbol:
                    holding.add_spot(pair.buy_spot)

            for ssym, spot in self.spots.items():
                if holding.symbol == spot.symbol:
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
            if pair.sell_spot.symbol != convert and pair.buy_spot.symbol != convert:
                add(pair.sell_spot.symbol, pair.buy_spot.symbol)

            elif pair.sell_spot.symbol == convert:
                add(pair.sell_spot.symbol, pair.buy_spot.symbol)

            elif pair.buy_spot.symbol == convert:
                add(pair.buy_spot.symbol, pair.sell_spot.symbol)

        # Spots
        for ssym, spot in self.spots.items():
            add(convert, spot.symbol)

        # Holdings
        for hsym, holding in self.holdings.items():
            if holding.symbol == convert:
                continue
            add(convert, holding.symbol)

        # Fees
        for fee_id, fee in self.fees.items():
            if fee.symbol == convert:
                continue
            add(convert, fee.symbol)

        return symbols

    def quotes(self, quotes: Quotes, convert: str):
        for sub_portfolio in self.subs:
            _logger.debug(f'quotes({sub_portfolio.name})')
            sub_portfolio.quotes(quotes, convert)

        self._quotes_transactions(quotes, convert)
        self._quotes_holdings(quotes, convert)
        self._quotes_fees(quotes, convert)

    def _quotes_transactions(self, quotes: Quotes, convert: str):
        _logger.debug(f'quotes_transactions({self.name})')

        transactions = cast(list[Transaction], sorted(self.transactions, key=sort_transactions))
        for transaction in transactions:

            if transaction.is_pair:
                pair = transaction.pair

                transaction.cprice = quotes.get(convert, pair.buy_spot.symbol)

                _logger.debug(f'transaction: {transaction.ttype} {transaction.date}')

                target_spot: Spot = None
                if pair.sell_spot.symbol == convert:
                    cquote = quotes.get(convert, pair.buy_spot.symbol)
                    _logger.debug(f'cquote: {cquote} ({pair.buy_spot.symbol})')

                    pair.value = cquote * pair.buy_spot.quantity
                    _logger.debug(f'A {pair.value}(value) = {cquote}(cquote) * {pair.buy_spot.quantity}(buy_spot.quantity)')

                    if transaction.ttype == 'buy':
                        pair.profit = pair.value - pair.sell_spot.quantity
                        _logger.debug(f'profit A: {pair.profit}(profit) = {pair.value}(value) - {pair.sell_spot.quantity}(sell_spot.quantity)')

                    elif transaction.ttype == 'sell':
                        pair.profit = pair.sell_spot.quantity - pair.value
                        _logger.debug(f'profit B: {pair.profit}(profit) = {pair.sell_spot.quantity}(sell_spot.quantity) - {pair.value}(value)')

                    pair.sell_spot.value = pair.sell_spot.quantity
                    pair.buy_spot.value = cquote * pair.buy_spot.quantity

                    _logger.debug(f'pair.sell_spot: {pair.sell_spot}')
                    _logger.debug(f'pair.buy_spot: {pair.buy_spot}')

                    # Target
                    target_spot = Spot(s=pair.sell_spot.symbol)
                    if transaction.target_f:
                        target_spot.value = cquote - transaction.target_f

                elif pair.buy_spot.symbol == convert:
                    raise NotImplementedError()

                else:

                    cquote = quotes.get(pair.sell_spot.symbol, pair.buy_spot.symbol)
                    _logger.debug(f'cquote: {cquote}')
                    sell_quote = quotes.get(convert, pair.sell_spot.symbol)
                    _logger.debug(f'sell_quote: {sell_quote}')
                    buy_quote = quotes.get(convert, pair.buy_spot.symbol)
                    _logger.debug(f'buy_quote: {buy_quote}')

                    sell_value = sell_quote * pair.sell_spot.quantity
                    pair.sell_spot.value = sell_value
                    _logger.debug(f'{sell_value}(sell_value) = {sell_quote}(sell_quote) * {pair.sell_spot.quantity}(pair.sell_spot.quantity)')

                    buy_value = buy_quote * pair.buy_spot.quantity
                    pair.buy_spot.value = buy_value
                    _logger.debug(f'{buy_value}(buy_value) = {buy_quote}(buy_quote) * {pair.buy_spot.quantity}(pair.buy_spot.quantity)')

                    if transaction.ttype == 'buy':
                        pair.profit = buy_value - sell_value
                        _logger.debug(f'profit Ca: {pair.profit} = {buy_value}(buy_value) - {sell_value}(sell_value)')

                    elif transaction.ttype == 'sell':
                        pair.profit = sell_value - buy_value
                        _logger.debug(f'profit Cb: {pair.profit} = {sell_value}(sell_value) - {buy_value}(buy_value)')

                    pair.value = buy_value

                    _logger.debug(f'pair.sell_spot: {pair.sell_spot}')
                    _logger.debug(f'pair.buy_spot: {pair.buy_spot}')

                    # Target
                    target_spot = Spot(s=pair.sell_spot.symbol)
                    if transaction.target:
                        target_spot.value = cquote - transaction.target_f


                transaction.profit = pair.profit

                # Target
                if transaction.state == 'open':
                    transaction.target_spot = target_spot

            else:
                spot = transaction.spot
                quote = quotes.get(convert, spot.symbol)

                spot.value = quote * spot.quantity
                spot.profit = spot.value
                spot.price = quote

                if transaction.ttype == 'in':
                    pass
                elif transaction.ttype == 'out':
                    spot.profit *= -1
                else:
                    raise ValueError(f'Unknown Transaction type non-pair: {transaction.ttype}')

                transaction.profit = spot.profit

    def _quotes_holdings(self, quotes: Quotes, convert: str):
        _logger.debug(f'quotes_holdings({self.name})')

        # Holdings
        for hsym, holding in self.holdings.items():
            if holding.symbol == convert:
                self.costs = Spot(s=holding.symbol)
                self.costs.quantity = holding.quantity * -1
                continue

            _logger.debug('--------------')
            _logger.debug(f'holding={holding.symbol}')

            quote = quotes.get(convert, holding.symbol)

            holding.quote = quote
            holding.value = quote * holding.quantity
            holding.profit = 0.0

            sorted_transactions = cast(list[Transaction], sorted(holding.transactions, key=sort_transactions))
            for transaction in sorted_transactions:

                _logger.debug(f'transaction: {transaction.date} {transaction.ttype} {transaction.pair_s}')
                _logger.debug(f' |  price: {transaction.price}')
                _logger.debug(f' |  quantity: {transaction.quantity}')
                _logger.debug(f' |  profit: {transaction.profit}')


                profit = 0.0

                if transaction.is_pair:
                    _logger.debug(f' |  sell_spot: {transaction.pair.sell_spot}')
                    _logger.debug(f' |  buy_spot: {transaction.pair.buy_spot}')

                    if transaction.profit is not None:
                        profit = transaction.profit

                    if holding.symbol == transaction.sell_symbol:
                        _logger.debug(' |  holding is transaction.sell_symbol')
                    elif holding.symbol == transaction.buy_symbol:
                        _logger.debug(' |  holding is transaction.buy_symbol')
                else:
                    _logger.debug(f' |  spot: {transaction.spot}')
                    profit = transaction.spot.profit

                holding.profit += profit

                _logger.debug(f' |  holding({holding.symbol}): profit={profit}    hp={holding.profit}')

    def _quotes_fees(self, quotes: Quotes, convert: str):
        _logger.debug(f'quotes_fees({self.name})')

        # Fees
        for fee_id, fee in self.fees.items():

            if fee.symbol == convert:
                self.fee_value += fee.quantity
            else:
                quote = quotes.get(convert, fee.symbol)
                self.fee_value += quote * fee.quantity
