#!/usr/bin/env python3

import sys
import signal
import shutil
import pandas as pd

from argparse import ArgumentParser, BooleanOptionalAction
from json import loads, dumps
from cmc import get_quotes as cmc_get_quotes
from sty import fg, bg, ef, rs
from datetime import datetime
from pathlib import Path
from portfolio import Portfolio
from transaction import Transaction
from spot import Spot
from apptypes import Quotes

class App():
    show_transactions: bool
    data_provider_id: str|None
    config: dict
    running: bool

    def __init__(self, config_path: str|None, show_transactions: bool = False, data_provider_id: str = 'cmc'):
        self.terminal = shutil.get_terminal_size((80, 20))
        self.show_transactions = show_transactions
        self.data_provider_id = data_provider_id

        if config_path is None:
            raise Exception('Config file not provided')

        with open(config_path, 'r') as f:
            self.config = loads(f.read())

    def run(self, basedir: Path):
        self.running = True

        portfolio = self._traverse(Path(basedir))
        portfolio.calc()

        quotes = self._get_quotes()
        portfolio.quotes(quotes)

        self._print_portfolio(portfolio)

    def shutdown(self, reason: str):
        print()
        print(f'-> shutting down: {reason}')

        self.running = False

    def _traverse(self, dir: Path, parent: Portfolio|None = None) -> Portfolio:
        portfolio = Portfolio(name=dir.name, parent=parent)

        for file in dir.iterdir():
            if file.is_dir():
                sub_portfolio = self._traverse(file, portfolio)
                portfolio.add_portfolio(sub_portfolio)

            elif file.is_file():
                if not str(file).endswith('.json'):
                    continue

                with open(file, 'r') as f:
                    json = loads(f.read())

                for pair in json:
                    for transaction_j in pair['transactions']:
                        transaction_o = Transaction(pair=pair['pair'], d=transaction_j)

                        portfolio.add_transaction(transaction_o)

        return portfolio

    def _get_quotes(self) -> Quotes:
        symbols = self.config['portfolio']['symbols']

        config = None
        for dp_config in self.config['data_providers']:
            if dp_config['enabled']:
                if self.data_provider_id is None:
                    # Take first.
                    config = dp_config
                else:
                    # Compare ID.
                    if self.data_provider_id == dp_config['id']:
                        config = dp_config
                        break

        data = None
        if config is not None:
            f = getattr(sys.modules[__name__], f'{config["id"]}_get_quotes')
            print(f'f = {f}')
            data = f(
                api_host=config['api']['host'],
                api_key=config['api']['key'],
                convert=self.config['convert'],
                symbols=symbols,
            )

            # print('----------- data -----------')
            # print(dumps(data, indent=2))
            # print('----------------------------')

        convert = self.config['convert']

        symbol_values: Quotes = {}
        if data is not None:
            for symbol in symbols:
                if symbol in data['data']:
                    sdata = data['data'][symbol]
                    first_q = sdata[0]
                    if convert in first_q['quote']:
                        symbol_values[symbol] = first_q['quote'][convert]['price']

        # print('----- symbol_values -----')
        # print(dumps(symbol_values, indent=2))
        # print('----------------------------')

        symbol_values['XRP'] = 5.0

        return symbol_values

    def _print_portfolio(self, portfolio: Portfolio):



        sell_symbols = ', '.join(list(portfolio.sell_symbols))
        buy_symbols = ', '.join(list(portfolio.buy_symbols))

        cost_spot = Spot(s=self.config['convert'])
        holdings = {
            'sym': [],
            'holding': [],
            'quote': [],
            'value': [],
        }
        for sym, spot in portfolio.holdings.items():
            if spot.quantity == 0.0:
                continue

            if spot.symbol == self.config['convert']:
                cost_spot.quantity = spot.quantity
            else:
                holdings['sym'].append(spot.symbol)
                holdings['holding'].append(spot.quantity)
                holdings['quote'].append(spot.quote)
                holdings['value'].append(spot.value)

        print()
        print('-' * self.terminal.columns)
        print(f'Portfolio: {portfolio.name} (level={portfolio.level})')
        print(f'Transactions: {portfolio.transactions_c}')

        if sell_symbols != '':
            print(f'Sell symbols: {sell_symbols}')
        if buy_symbols != '':
            print(f'Buy  symbols: {buy_symbols}')



        print(f'Costs: {cost_spot.quantity} {cost_spot.symbol}')

        if len(holdings['sym']) > 0:
            df = pd.DataFrame(data=holdings)
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
    parser.add_argument('-c', '--config', type=str, nargs='?', required=False, help='Path to Config File', default=[None])
    parser.add_argument('-d', '--basedir', type=str, nargs='?', required=False, help='Path to directory', default=[None])
    parser.add_argument('-p', '--dataprovider', type=str, nargs='?', required=False, help='ID', default='cmc')
    parser.add_argument('-t', '--transactions', action=BooleanOptionalAction, help='Show transactions', default=False)

    args = parser.parse_args()
    # print(args)

    app = App(args.config, args.transactions, args.dataprovider)

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    basedir = Path(args.basedir)
    try:
        app.run(basedir)
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
