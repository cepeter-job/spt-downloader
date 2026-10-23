"""Expected monetary values for valid synthetic PPh21 fixtures only."""
from decimal import Decimal


def money(value):
    return float(Decimal(value.replace('.', '').replace(',', '.')))


def money_row(values, *, ia=False):
    expected = list(values)
    for index in (6, 8 if ia else 7):
        expected[index] = money(expected[index])
    if ia:
        expected[7] = float(Decimal(expected[7].replace(',', '.')) / 100)
    return expected
