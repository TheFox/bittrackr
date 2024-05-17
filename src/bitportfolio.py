#!/usr/bin/env python3

import sys
import signal
import shutil
from typing import cast
import pandas as pd

from argparse import ArgumentParser, BooleanOptionalAction
from json import loads, load, dumps, dump
from cmc import get_quotes as cmc_get_quotes
from sty import fg, bg, ef, rs
from pathlib import Path
from portfolio import Portfolio
from transaction import Transaction
from spot import Spot
from apptypes import ConvertSymbols
from json_helper import ComplexEncoder
from portfolio import Holding
from quotes import Quotes

def _sort_holdings(item: tuple[str, Holding]):
    value = item[1].value
    if value is None:
        return 0.0
    return value

class App():
    show_transactions: bool
    data_provider_id: str|None
    config: dict
    running: bool

    def __init__(self, base_dir: str|None = None, config_path: str|None = None, show_transactions: bool = False, data_provider_id: str = 'cmc', quotes_file: str|None = None, change_dir: str|None = None, max_depth: int|None = None, filter_symbol: str|None = None, filter_ttype: bool|None = None, save: bool|None = None):
        self.terminal = shutil.get_terminal_size((80, 20))

        self.running = False
        self.show_transactions = show_transactions
        self.data_provider_id = data_provider_id

        if change_dir is None:
            self.change_dir = Path('.')
        else:
            self.change_dir = Path(change_dir)

        if base_dir is None:
            self.base_dir = self.change_dir / 'portfolios'
        else:
            self.base_dir = Path(base_dir)

        if config_path is None:
            self.config_path = self.change_dir / 'config.json'
        else:
            self.config_path = Path(config_path)

        if quotes_file is None:
            self.quotes_file = None
        else:
            self.quotes_file = Path(quotes_file)

        # print(f'-> change_dir: {self.change_dir}')
        # print(f'-> base_dir: {self.base_dir}')
        # print(f'-> config_path: {self.config_path}')
        # print(f'-> quotes_file: {self.quotes_file}')

        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = loads(f.read())

        self.max_depth = max_depth
        self.filter_symbol = filter_symbol
        self.filter_ttype = filter_ttype
        self.save = save

    def run(self):
        self.running = True

        portfolio = self._traverse(self.base_dir)
        portfolio.calc()

        # print('------- portfolio -------')
        # print(dumps(portfolio, indent=2, cls=ComplexEncoder))
        # print('------------------------')

        psymbols = portfolio.get_convert_symbols(self.config['convert'])
        # print(f'----- psymbols -----')
        # print(dumps(psymbols, indent=2))
        # print('----------------------------')

        # load_quotes = False
        # if self.quotes_file is not None:
        #     if not self.save or self.save is None:
        #         print(f'-> load quotes file: {self.quotes_file}')
        #         with open(self.quotes_file, 'r') as f:
        #             quotes_j = load(f)
        #             quotes = Quotes(quotes_j)
        #             load_quotes = True

        quotes = self._get_quotes(psymbols, self.config['convert'])
        # print(f'----- quotes -----')
        # print(dumps(quotes, indent=2, cls=ComplexEncoder))
        # print('----------------------------')

        if self.quotes_file is not None:
            if self.save:
                print(f'-> save quotes file: {self.quotes_file}')
                with open(self.quotes_file, 'w') as f:
                    dump(quotes.to_json(), f, indent=2)

        # print('------- quotes -------')
        # print(dumps(quotes, indent=2, cls=ComplexEncoder))
        # print('------------------------')

        portfolio.quotes(quotes, self.config['convert'])
        self._print_portfolio(portfolio)

    def shutdown(self, reason: str):
        print()
        print(f'-> shutting down: {reason}')

        self.running = False

    def _traverse(self, dir: Path, parent: Portfolio|None = None, level: int = 0) -> Portfolio:
        portfolio = Portfolio(name=dir.name, parent=parent)

        for file in dir.iterdir():
            if file.is_dir():
                nlevel = level + 1
                if self.max_depth is not None and nlevel >= self.max_depth:
                    continue

                sub_portfolio = self._traverse(file, portfolio, nlevel)
                portfolio.add_portfolio(sub_portfolio)

            elif file.is_file():
                if not str(file).endswith('.json'):
                    continue

                with open(file, 'r') as f:
                    json = loads(f.read())

                for pair in json:
                    for transaction_j in pair['transactions']:
                        transaction_o = Transaction(pair=pair['pair'], d=transaction_j)

                        handle_trx = True

                        if self.filter_symbol is not None:
                            if transaction_o.sell_symbol != self.filter_symbol and transaction_o.buy_symbol != self.filter_symbol:
                                handle_trx = False

                        if self.filter_ttype is not None:
                            if transaction_o.ttype != self.filter_ttype:
                                handle_trx = False

                        # print(f'-> handle_trx: {transaction_o} {handle_trx}')

                        if handle_trx:
                            portfolio.add_transaction(transaction_o)

        return portfolio

    def _get_quotes(self, symbols: ConvertSymbols, convert: str) -> Quotes:
        dp_config = self.config['data_provider']
        if dp_config['id'] == 'cmc':
            data_fetch_func = cmc_get_quotes
        else:
            raise ValueError(f'Unknown data provider: {dp_config["id"]}')

        quotes = Quotes()

        for convert, sym_list in symbols.items():
            # print(f'-> convert {convert} {sym_list}')
            data = data_fetch_func(
                api_host=dp_config['api']['host'],
                api_key=dp_config['api']['key'],
                convert=convert,
                symbols=sym_list,
            )

            # print('----------- data -----------')
            # print(dumps(data, indent=2))
            # print('----------------------------')

            for symbol in sym_list:
                if symbol in data['data']:
                    sdata = data['data'][symbol]

                    if convert in sdata[0]['quote']:
                        quotes.add(convert, symbol, sdata[0]['quote'][convert]['price'])

        # print(f'----- quotes -----')
        # print(dumps(quotes, indent=2, cls=ComplexEncoder))
        # print('--------------------------')

        return quotes

    def _print_portfolio(self, portfolio: Portfolio):
        if portfolio.transactions_c == 0:
            return

        sell_symbols = ', '.join(list(portfolio.sell_symbols))
        buy_symbols = ', '.join(list(portfolio.buy_symbols))

        cost_spot = Spot(s=self.config['convert']) #  TODO move to portfolio
        holdings = {
            'sym': [],
            'quant': [],
            'quote': [],
            'value': [],
            'trx': [],
        }
        sorted_holdings = sorted(portfolio.holdings.items(), key=_sort_holdings, reverse=True)
        total_value = 0.0
        for hsym, holding in sorted_holdings:
            if holding.symbol == self.config['convert']:
                cost_spot.quantity = holding.quantity * -1
            else:
                holdings['sym'].append(holding.symbol)
                holdings['quant'].append(holding.quantity)
                holdings['quote'].append(holding.quote)
                holdings['value'].append(holding.value)
                holdings['trx'].append(holding.trx_count)

            total_value += holding.value

        profit = total_value - cost_spot.quantity

        print('-' * self.terminal.columns)
        print(f'Portfolio: {portfolio.name} (level={portfolio.level})')
        print(f'Transactions: {portfolio.transactions_c}')

        if sell_symbols != '':
            print(f'Sell symbols: {sell_symbols}')
        if buy_symbols != '':
            print(f'Buy  symbols: {buy_symbols}')

        if cost_spot.quantity >= 0.0:
            costs_color = fg.red
        else:
            costs_color = fg.black

        if profit >= 0:
            profit_color = fg.black
        else:
            profit_color = fg.red

        print(f'Fees:   {portfolio.fee_value:>10.2f} {self.config["convert"]}')
        print(f'Costs:  {costs_color}{cost_spot.quantity:>10.2f} {cost_spot.symbol}{rs.all}')
        print(f'Value:  {total_value:>10.2f} {self.config["convert"]}')
        print(f'Profit: {profit_color}{profit:>10.2f} {self.config["convert"]}{rs.all}')

        if len(holdings['sym']) > 0:
            df = pd.DataFrame(data=holdings)
            df['quant'] = df['quant'].apply(lambda x: '{:.5f}'.format(x))
            df['quote'] = df['quote'].apply(lambda x: '{:.6f}'.format(x))
            df['value'] = df['value'].apply(lambda x: '{:.2f}'.format(x))

            df.rename(columns={'price': f'price({self.config["convert"]})'}, inplace=True)
            df.rename(columns={'quote': f'quote({self.config["convert"]})'}, inplace=True)
            df.rename(columns={'value': f'value({self.config["convert"]})'}, inplace=True)

            df_s = df.to_string(index=False)
            print()
            print(df_s)

        if self.show_transactions:
            transactions = {
                'date': [],
                'type': [],
                'pair': [],
                'quant': [],
                'price': [],
                'value': [],
                'profit': [],
                'sell': [],
                'buy': [],
            }
            sorted_transactions = sorted(portfolio.transactions, key=lambda t: t.date)
            sorted_transactions = cast(list[Transaction], sorted_transactions)
            for transaction in sorted_transactions:

                transactions['date'].append(transaction.date)
                transactions['type'].append(transaction.ttype)
                if transaction.is_pair:
                    transactions['price'].append(transaction.price)
                    transactions['pair'].append(transaction.pair.name)
                    transactions['quant'].append(transaction.pair.buy_spot.quantity)
                    transactions['value'].append(transaction.pair.value)
                    transactions['profit'].append(transaction.pair.profit)

                    if transaction.ttype == 'buy':
                        transactions['sell'].append(transaction.pair.sell_spot.to_str())
                        transactions['buy'].append(transaction.pair.buy_spot.to_str())
                    elif transaction.ttype == 'sell':
                        transactions['sell'].append(transaction.pair.buy_spot.to_str())
                        transactions['buy'].append(transaction.pair.sell_spot.to_str())
                    else:
                        raise ValueError(f'Unknown Transaction type: {transaction.ttype}')
                else:
                    transactions['price'].append(0.0)
                    transactions['pair'].append(transaction.spot.symbol)
                    transactions['quant'].append(transaction.spot.quantity)
                    transactions['value'].append(transaction.spot.value)
                    transactions['profit'].append(transaction.spot.profit)
                    transactions['sell'].append('---')
                    transactions['buy'].append('---')

            if len(transactions['pair']) > 0:
                try:
                    df = pd.DataFrame(data=transactions)
                except ValueError as error:
                    print(f'----- transactions -----')
                    print(dumps(transactions, indent=2))
                    print('----------------------------')
                    raise error

                df.rename(columns={'price': f'price({self.config["convert"]})'}, inplace=True)
                df.rename(columns={'quote': f'quote({self.config["convert"]})'}, inplace=True)
                df.rename(columns={'value': f'value({self.config["convert"]})'}, inplace=True)
                df.rename(columns={'profit': f'profit({self.config["convert"]})'}, inplace=True)

                df_s = df.to_string(index=False)
                print()
                print(df_s)

        subs = sorted(portfolio.subs, key=lambda p: p.name)
        for sub_portfolio in subs:
            self._print_portfolio(sub_portfolio)

def main():
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    #pd.options.display.float_format = '{:,.2f}'.format

    parser = ArgumentParser(prog='bitportfolio', description='BitPortfolio')
    parser.add_argument('-c', '--config', type=str, nargs='?', required=False, help='Path to Config File')
    parser.add_argument('-d', '--basedir', type=str, nargs='?', required=False, help='Path to directory')
    parser.add_argument('-p', '--dataprovider', type=str, nargs='?', required=False, help='ID', default='cmc')
    parser.add_argument('-t', '--transactions', action=BooleanOptionalAction, help='Show transactions', default=False)
    parser.add_argument('-qf', '--quotes-file', type=str, nargs='?', required=False, help='Save/load quotes from file')
    parser.add_argument('-C', '--chdir', type=str, nargs='?', required=False, help='Change directory and look for files')
    parser.add_argument('-l', '--max-depth', type=int, nargs='?', required=False, help='Max directory depth')
    parser.add_argument('-s', '--symbol', type=str, nargs='?', required=False, help='Handle only Transactions with given symbol')
    parser.add_argument('--buy', action=BooleanOptionalAction, help='Show only buy Transactions')
    parser.add_argument('--sell', action=BooleanOptionalAction, help='Show only sell Transactions')
    parser.add_argument('--save', action=BooleanOptionalAction, help='Save Quotes file')

    args = parser.parse_args()
    # print(args)

    filter_ttype = None
    if args.buy:
        filter_ttype = 'buy'
    elif args.sell:
        filter_ttype = 'sell'

    app = App(
        base_dir=args.basedir,
        config_path=args.config,
        show_transactions=args.transactions,
        data_provider_id=args.dataprovider,
        quotes_file=args.quotes_file,
        change_dir=args.chdir,
        max_depth=args.max_depth,
        filter_symbol=args.symbol,
        filter_ttype=filter_ttype,
        save=args.save,
    )

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
