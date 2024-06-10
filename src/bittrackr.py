#!/usr/bin/env python3

import signal
import argparse
import shutil
from json import loads
from time import sleep
from cmc import get_quotes as cmc_get_quotes
from sty import fg, bg, ef, rs
from datetime import datetime

CLEAR_SCREEN='\033[2J'
JUMP_BEGINNING='\033[1;1H'

def status(text: str):
    # Jump to line 3.
    print('\033[3;1H', end='', flush=True)
    print(f'\033[2K   -> {text}\033[1G', end='', flush=True)
    sleep(0.1)

def clear():
    # Jump to line 3.
    print('\033[3;1H', end='', flush=True)
    print('\033[2K\033[1G', end='', flush=True)

class App():
    config: dict
    _rest_updates: int
    running: bool
    data: dict
    screen: dict

    def __init__(self, config_path: str|None, scenario: str = 'all', update_interval: int|None = None, max_updates: int|None = None):
        print(f'-> config path: {config_path}')
        if config_path is None:
            self.config = self._default_config()
        else:
            with open(config_path, 'r') as f:
                config = loads(f.read())

            dc = self._default_config()
            self.config = {
                **dc,
                **config,
            }

        self.scenario = scenario
        self.symbols = ["BTC", "ETH", "SOL"]
        if self.scenario in self.config['scenario']:
            self.symbols = self.config['scenario'][self.scenario]

        if update_interval is not None:
            self.config['update_interval'] = update_interval

        if max_updates is None:
            self._rest_updates = 999999
        else:
            self._rest_updates = max_updates

        self.data = {}
        for sym in self.symbols:
            self.data[sym] = {
                'symbol': sym,
                'direction': 0,
                'prev_price': None,
                'dp': {
                    'quote_price': None,
                    'last_updated': None,
                    'volume_24h': None,
                    'volume_change_24h': None,
                    'percent_change_24h': None,
                    'market_cap_dominance': None,
                },
            }

        terminal = shutil.get_terminal_size((80, 20))
        self.screen = {
            'lines': terminal.lines,
            'columns': terminal.columns,
        }

    def run(self):
        self.running = True

        sleep_list = list(reversed(list(range(1, self.config['update_interval']))))

        # Clear screen
        print(CLEAR_SCREEN, end='', flush=True)

        # Jump to top left.
        print(JUMP_BEGINNING, end='', flush=True)

        cycle_n = 0
        while self.running and self._rest_updates > 0:
            cycle_n += 1

            # Jump to top left.
            print(JUMP_BEGINNING, end='', flush=True)

            print(f'Update Interval: {self.config["update_interval"]} | Rest Updates: {self._rest_updates} | Scenario: {self.scenario}')

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f'Last update: {now}')

            self._data_update()
            self._screen_update()

            self._rest_updates -= 1

            if self._rest_updates == 0:
                self.shutdown('max updates reached')
                break

            for n in sleep_list:
                status(f'Next update in {n}')
                sleep(1)
                if not self.running:
                    break

    def _data_update(self):
        status('Data update')
        dp_config = self.config['data_provider']

        if dp_config['id'] == 'default':
            raise ValueError('Found only default config')
        elif dp_config['id'] == 'cmc':
            self._data_update_from_cmc(dp_config)
        else:
            raise ValueError(f'Unknown data provider: {dp_config["id"]}')

    def _data_update_from_cmc(self, dp_config: dict):
        status('Get data from CMC ...')
        response = cmc_get_quotes(
            api_host=dp_config['api']['host'],
            api_key=dp_config['api']['key'],
            convert=self.config['convert'],
            symbols=self.symbols,
        )
        for sym, sdata in response['data'].items():
            status(f'Process sym "{sym}" ...')
            if len(sdata) == 0:
                continue

            fsdata = sdata[0]
            fiat_quote = fsdata['quote'][self.config['convert']]

            self.data[sym]['dp']['quote_price'] = fiat_quote['price']
            self.data[sym]['dp']['last_updated'] = fiat_quote['last_updated']
            self.data[sym]['dp']['volume_24h'] = fiat_quote['volume_24h']
            self.data[sym]['dp']['volume_change_24h'] = fiat_quote['volume_change_24h']
            self.data[sym]['dp']['percent_change_24h'] = fiat_quote['percent_change_24h']
            self.data[sym]['dp']['market_cap_dominance'] = fiat_quote['market_cap_dominance']

            if self.data[sym]['prev_price'] is not None:
                if self.data[sym]['dp']['quote_price'] > self.data[sym]['prev_price']:
                    self.data[sym]['direction'] = 1
                elif self.data[sym]['dp']['quote_price'] < self.data[sym]['prev_price']:
                    self.data[sym]['direction'] = -1
                else:
                    self.data[sym]['direction'] = 0

            self.data[sym]['prev_price'] = self.data[sym]['dp']['quote_price']

        status(f'Processed {len(self.data)} symbols')

    def _screen_update(self):
        print()
        print()
        print('SYM      PRICE      24%   24Vol%            24Vol  Dominance')
        print('------------------------------------------------------------')

        for sym, coin in self.data.items():
            out_r = '{:5s} {:>8.2f}{} {:>8.2f} {:>8.2f} {:>16.2f}     {:>6.2f}'.format(
                sym,
                coin['dp']['quote_price'],
                rs.all,
                coin['dp']['percent_change_24h'],
                coin['dp']['volume_change_24h'],
                coin['dp']['volume_24h'],
                coin['dp']['market_cap_dominance'],
            )

            if coin['direction'] == 1:
                fg_color = fg.green
            elif coin['direction'] == -1:
                fg_color = fg.red
            else:
                fg_color = rs.all

            row_s = fg_color + out_r
            print(row_s, end='', flush=True)
            sleep(0.1)
            print('\033[1G', end='', flush=True)
            sleep(0.05)
            print('\033[1B', end='', flush=True)
            sleep(0.1)

            if not self.running:
                break

        print('\033[1E', end='', flush=True)

    def shutdown(self, reason: str):
        print()
        print(f'-> shutting down: {reason}')
        self.running = False

    def _default_config(self):
        return {
            'update_interval': 60,
            'convert': 'USD',
            'scenario': {
                'all': ['BTC', 'ETH', 'BNB', 'SOL'],
                'memes': ['DOGE', 'SHIB']
            },
            'data_provider': {
                'id': 'default',
            },
        }

def main():
    parser = argparse.ArgumentParser(prog='bittrackr', description='BitTrackr')
    parser.add_argument('-c', '--config', type=str, nargs='?', required=False, help='Path to Config File', default='var/config.json')
    parser.add_argument('-s', '--scenario', type=str, nargs='?', required=False, help='Scenario', default='all')
    parser.add_argument('-i', '--update-interval', type=int, nargs='?', required=False, help='Overwrite update_interval in config', default=120)
    parser.add_argument('-u', '--max-updates', type=int, nargs='?', required=False, help='Max Updates')

    args = parser.parse_args()
    print(args)

    app = App(
        args.config,
        scenario=args.scenario,
        update_interval=args.update_interval,
        max_updates=args.max_updates,
    )

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
