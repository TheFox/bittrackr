
QuotesDict = dict[str, dict[str, float]]

class Quotes():
    symbols: QuotesDict

    def __init__(self, symbols: dict = {}) -> None:
        self.symbols = symbols

    def add(self, convert: str, symbol: str, val: float):
        if convert not in self.symbols:
            self.symbols[convert] = {}

        if symbol not in self.symbols[convert]:
            self.symbols[convert][symbol] = 0.0

        self.symbols[convert][symbol] = val

    def get(self, convert: str, symbol: str) -> float:
        if convert == symbol:
            return 1.0

        if convert not in self.symbols:
            raise ValueError(f'convert not found in quotes: {convert}: {self.symbols.keys()}')

        if symbol not in self.symbols[convert]:
            raise ValueError(f'symbol not found in quotes: convert={convert} symbol={symbol}')

        return self.symbols[convert][symbol]
