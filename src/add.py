#!/usr/bin/env python3

import signal
from logging import getLogger, basicConfig
from typing import Optional
from argparse import ArgumentParser, BooleanOptionalAction
from yaml import safe_load, dump
from os.path import isfile

_logger = getLogger(f'app.{__name__}')

class App():
    show_transactions: bool
    data_provider_id: str|None
    config: dict
    running: bool

    def __init__(self,
                 file: str,
                 date: str,
                 ttype: str,
                 symbol: str,
                 quantity: float,
                 price: float,
                 source: str,
                 target: Optional[float] = None,
                 log_level: str = 'INFO',
                 ):

        logConfig = {
            'level': log_level,
            'format': '%(asctime)s %(process)d %(levelname)s %(name)s %(message)s',
        }
        basicConfig(**logConfig)

        self.running = False
        self.file = file
        self.date = date
        self.ttype = ttype
        self.symbol = symbol
        self.quantity = float(quantity)
        self.price = float(price)
        if target:
            self.target = float(target)
        else:
            self.target = None
        self.source = source

    def run(self):
        self.running = True

        if isfile(self.file):
            _logger.info(f'load file: {self.file}')
            with open(self.file) as file:
                yaml = safe_load(file)
        else:
            yaml = {
                'ignore': False,
                'sources': []
            }

        new_transaction = {
            'date': self.date,
            'type': self.ttype,
            'price': self.price,
        }
        if self.target:
            new_transaction['target'] = self.target
        new_transaction.update({
            'quantity': self.quantity,
        })

        found_source = False
        for source in yaml['sources']:
            print(source)
            if source['source'] == self.source:
                found_source = True
        if not found_source:
            yaml['sources'].append({
                'source': self.source,
                'pairs': []
            })

        found_pair = False
        for source in yaml['sources']:
            if source['source'] == self.source:
                for pair in source['pairs']:
                    if pair['pair'] == self.symbol:
                        found_pair = True
        if not found_pair:
            i = 0
            for source in yaml['sources']:
                if source['source'] == self.source:
                    yaml['sources'][i]['pairs'].append({
                        'pair': self.symbol,
                        'transactions': []
                    })
                i += 1

        for source in yaml['sources']:
            if source['source'] == self.source:
                for pair in source['pairs']:
                    if pair['pair'] == self.symbol:
                        pair['transactions'].append(new_transaction)

        with open(self.file, 'w') as file:
            dump(yaml, file, sort_keys=False)

    def shutdown(self, reason: str):
        print()
        print(f'-> shutting down: {reason}')

        self.running = False

def main():
    parser = ArgumentParser(prog='bitportfolio', description='BitPortfolio')
    parser.add_argument('--log-level', type=str, nargs='?', required=False, help='Log Level', default='WARN')
    parser.add_argument('-f', '--file', type=str, nargs='?', required=True, help='File')
    parser.add_argument('-d', '--date', type=str, nargs='?', required=False, help='Date')
    parser.add_argument('-s', '--symbol', type=str, nargs='?', required=False, help='Symbol')
    parser.add_argument('-b', '--buy', action=BooleanOptionalAction, help='Buy')
    parser.add_argument('--sell', action=BooleanOptionalAction, help='Sell')
    parser.add_argument('-q', '--quantity', type=int, nargs='?', required=False, help='Quantity')
    parser.add_argument('-p', '--price', type=float, nargs='?', required=False, help='Price')
    parser.add_argument('-t', '--target', type=float, nargs='?', required=False, help='Target')
    parser.add_argument('--src', '--source', type=str, required=False, help='Source')
    parser.add_argument('arg', type=str, nargs='?', help='source,pair,date,ttype,quantity,price,target')

    args = parser.parse_args()
    print(args)

    ttype = None
    if args.buy:
        ttype = 'buy'
    elif args.sell:
        ttype = 'sell'
    else:
        ttype = 'buy'

    if args.arg:
        items = args.arg.split(',')
        print(items)
        items_len = len(items)
        if items_len == 6:
            items.append(None)
        source, symbol, date, ttype, quantity, price, target = items
        app = App(
            file=args.file,
            date=date.strip(),
            ttype=ttype.strip(),
            symbol=symbol.strip(),
            quantity=quantity,
            price=price,
            target=target,
            source=source.strip(),
            log_level=args.log_level,
        )
    else:
        app = App(
            file=args.file,
            date=args.date,
            ttype=ttype,
            symbol=args.symbol,
            quantity=args.quantity,
            price=args.price,
            source=args.src,
            target=args.target,
            log_level=args.log_level,
        )

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
