#!/usr/bin/env python3

from requests import post
from os import getenv
from time import sleep
from signal import signal, SIGINT
from typing import Optional
from argparse import ArgumentParser, BooleanOptionalAction
from yaml import safe_load
from json import loads, dumps
from json.decoder import JSONDecodeError
from pathlib import Path
from portfolio import Portfolio
from transaction import Transaction
from json_helper import ComplexEncoder


class App():
    base_dir: Path
    running: bool
    wait_list: list[Transaction]

    def __init__(self,
        base_dir: Optional[str] = None,
        url: Optional[str] = None,
    ):
        self.running = False
        self.base_dir = Path(base_dir)
        self.url = url
        self.wait_list = []

    def run(self):
        self.running = True
        portfolio = self._traverse(self.base_dir)

        self._process(portfolio.transactions)
        self._process(self.wait_list, False)

    def _process(self, transactions: list[Transaction], use_wait_list: bool = True):
        print(f'-> transactions: {len(transactions)}, {use_wait_list}')
        for transaction in transactions:
            #sleep(0.1)
            print(f'-> transaction: {transaction.date}')
            self._send(transaction, use_wait_list)
            if not self.running:
                break

    def _send(self, transaction: Transaction, use_wait_list: bool = True):
        payload = {
            'portfolio_id': 2,
            'source': transaction.source,
            'date': str(transaction.date) + '+02:00',
            'type': transaction.ttype,
            'quantity': transaction.quantity,
        }

        if transaction.pair_s:
            payload['pair'] = transaction.pair_s
        if transaction.price:
            payload['price'] = transaction.price
        if transaction.cost:
            payload['costs'] = transaction.cost
        if transaction.target_f:
            payload['target'] = transaction.target_f
        if transaction.fee:
            payload['fee'] = {
                'quantity': transaction.fee.quantity,
                'symbol': transaction.fee.symbol,
            }
        if transaction.note:
            payload['note'] = transaction.note
        if transaction.state:
            payload['state'] = transaction.state
        if transaction.close_date:
            payload['close_date'] = transaction.close_date + '+02:00'

        response = post(
            self.url,
            json=payload,
            headers={'Content-Type': 'application/json'},
        )
        print(f'-> code: {response.status_code}')
        try:
            body = loads(response.content)
        except JSONDecodeError as error:
            print(response.content)
            return

        if response.status_code == 200:
            print(f'-> status: {body["status"]}')

            if body['status'] == 'OK':
                pass
            elif body['status'] == 'wait':
                if use_wait_list:
                    self.wait_list.append(transaction)
                else:
                    print('-> we got wait response but use_wait_list is false')
                    print(f'----- PAYLOAD -----')
                    print(dumps(payload, indent=2, cls=ComplexEncoder))
                    print('--------------------')
                    print(f'----- ERROR -----')
                    print(dumps(body, indent=2, cls=ComplexEncoder))
                    print('------------------')
                    self.running = False

        elif response.status_code == 400:
            print(f'----- PAYLOAD -----')
            print(dumps(payload, indent=2, cls=ComplexEncoder))
            print('--------------------')
            print(f'----- ERROR -----')
            print(dumps(body, indent=2, cls=ComplexEncoder))
            print('------------------')
            self.running = False

    def _traverse(self, dir: Path, parent: Optional[Portfolio] = None, level: int = 0) -> Portfolio:
        portfolio = Portfolio(name=dir.name, parent=parent)

        for file in dir.iterdir():
            if file.is_dir():
                nlevel = portfolio.level + 1
                sub_portfolio = self._traverse(file, portfolio, nlevel)
                portfolio.add_portfolio(sub_portfolio)

            elif file.is_file():
                raw_data = None
                with open(file, 'r') as f:
                    if str(file).endswith('.json'):
                        raw_data = loads(f.read())
                    if str(file).endswith('.yml'):
                        raw_data = safe_load(f)

                if 'ignore' in raw_data:
                    if raw_data['ignore']:
                        continue

                if 'sources' not in raw_data:
                    raise ValueError(f'No sources-field found in file: {file}')

                for source in raw_data['sources']:
                    if 'pairs' in source:
                        pairs = source['pairs']
                    if 'ignore' in source:
                        if source['ignore']:
                            continue

                    for pair in pairs:
                        if 'ignore' in pair and pair['ignore']:
                            continue

                        if 'transactions' not in pair:
                            continue

                        for transaction_j in pair['transactions']:
                            transaction_o = Transaction(
                                source=source['source'],
                                pair=pair['pair'],
                                d=transaction_j,
                            )

                            if transaction_o.ignore:
                                continue

                            portfolio.add_transaction(transaction_o)

        return portfolio

    def shutdown(self, reason: str):
        print()
        print(f'-> shutting down: {reason}')

        self.running = False

def main():
    wait = int(getenv('WAIT', 0))
    if wait > 0:
        print(f'-> wait {wait} seconds')
        sleep(wait)

    parser = ArgumentParser(prog='export', description='Export')
    parser.add_argument('-d', '--basedir', type=str, nargs='?', required=False, help='Path to directory')
    parser.add_argument('-u', '--url', type=str, nargs='?', required=False, help='Path to directory')

    args = parser.parse_args()
    print(args)

    app = App(
        base_dir=args.basedir,
        url=args.url,
    )

    signal(SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
