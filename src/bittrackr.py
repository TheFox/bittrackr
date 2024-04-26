#!/usr/bin/env python3

import signal
import argparse
from json import loads

class App():
    config: dict

    def __init__(self, config_path: str|None):
        print(f'-> config path: {config_path}')
        if config_path is None:
            self.config = self._default_config()
        else:
            with open(config_path, 'r') as f:
                config = loads(f.read())
            self.config = config

    def run(self):
        pass

    def shutdown(self, reason: str):
        print(f'-> shutting down: {reason}')

    def _default_config(self):
        return {}

def main():
    parser = argparse.ArgumentParser(prog='bittrackr', description='BitTrackr')
    parser.add_argument('-c', '--config', type=str, nargs=1, required=False, help='Path to Config File', default='config.json')

    args = parser.parse_args()
    print(args)

    app = App(args.config)

    signal.signal(signal.SIGINT, lambda sig, frame: app.shutdown('SIGINT'))

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown('KeyboardInterrupt')

if __name__ == '__main__':
    main()
