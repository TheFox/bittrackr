#!/usr/bin/env python3

import sys
import signal
import shutil
from argparse import ArgumentParser, BooleanOptionalAction
from json import loads, dumps
from cmc import get_quotes as cmc_get_quotes
from sty import fg, bg, ef, rs
from datetime import datetime
from pathlib import Path
from portfolio import Portfolio
from transaction import Transaction
from apptypes import Quotes

class App():
    show_transactions: bool
    data_provider_id: str|None
    config: dict
    running: bool
    quotes: dict

    def __init__(self, config_path: str|None, show_transactions: bool = False, data_provider_id: str = 'cmc'):
        print(f'-> config path: {config_path}')

        self.show_transactions = show_transactions
        self.data_provider_id = data_provider_id

        self.quotes = {}

        if config_path is None:
            raise Exception('Config file not provided')

        with open(config_path, 'r') as f:
            self.config = loads(f.read())

    def run(self, basedir: Path):
        self.running = True

        print(f'-> basedir.name={basedir.name}')

        portfolio = self._traverse(Path(basedir))
        portfolio.calc()

        self.quotes = self._get_quotes()

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

                print(f'-> file: {file}')

                for pair in json:
                    for transaction_j in pair['transactions']:
                        transaction_o = Transaction(pair=pair['pair'], d=transaction_j)

                        portfolio.add_transaction(transaction_o)

        return portfolio

    def _get_quotes(self) -> Quotes:
        print(f'-> _get_quotes()')
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

        data = {'data': {}}
        if config is not None:
            f = getattr(sys.modules[__name__], f'{config["id"]}_get_quotes')
            print(f'f = {f}')
            data = f(
                api_host=config['api']['host'],
                api_key=config['api']['key'],
                convert=self.config['convert'],
                symbols=symbols,
            )

            print('----------- data -----------')
            print(dumps(data, indent=2))
            print('----------------------------')

        convert = self.config['convert']

        symbol_values: Quotes = {}
        for symbol in symbols:
            if symbol in data['data']:
                symbol_values[symbol] = data['data'][symbol][0]['quote'][convert]['price']

        print('----- symbol_values -----')
        print(dumps(symbol_values, indent=2))
        print('----------------------------')

        symbol_values['XRP'] = 5.0

        return symbol_values

    def _print_portfolio(self, portfolio: Portfolio):

        terminal = shutil.get_terminal_size((80, 20))

        sell_symbols = ', '.join(list(portfolio.sell_symbols))
        buy_symbols = ', '.join(list(portfolio.buy_symbols))

        print('-' * terminal.columns)
        print(f'portfolio: {portfolio.name} (level={portfolio.level})')
        print(f'    transactions: {portfolio.transactions_c}')
        if sell_symbols != '':
            print(f'    sell symbols: {sell_symbols}')
        if buy_symbols != '':
            print(f'    buy  symbols: {buy_symbols}')

        for pname, pair in portfolio.pairs.items():
            print(f'---------------------------')
            print(f'    pair.name: {pair.name}')
            print(f'    pair.sell_spot: {pair.sell_spot}')
            print(f'    pair.buy_spot: {pair.buy_spot}')

        costs = []
        for sym, spot in portfolio.holdings.items():
            if spot.quantity == 0.0:
                continue

            if spot.quantity <= 0:
                costs.append(spot)
            else:
                print(f'-> total: {spot}')

        for spot in costs:
            print(f'-> cost: {spot}')

        subs = sorted(portfolio.subs, key=lambda p: p.name)
        for sub_portfolio in subs:
            self._print_portfolio(sub_portfolio)

def main():
    parser = ArgumentParser(prog='bitportfolio', description='BitPortfolio')
    parser.add_argument('-c', '--config', type=str, nargs='?', required=False, help='Path to Config File', default=[None])
    parser.add_argument('-d', '--basedir', type=str, nargs='?', required=False, help='Path to directory', default=[None])
    parser.add_argument('-p', '--dataprovider', type=str, nargs='?', required=False, help='ID', default='cmc')
    parser.add_argument('-t', '--transactions', action=BooleanOptionalAction, help='Show transactions', default=False)

    args = parser.parse_args()
    print(args)

    app = App(args.config, args.transactions, args.dataprovider)

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    basedir = Path(args.basedir)
    try:
        app.run(basedir)
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
