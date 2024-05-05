import decimal
import logging
from decimal import Decimal


log = logging.getLogger(__name__)

def maxint(string):
    if len(string) > 5:
        return 99999
    return int(string)


def ratio(x: int, y: int) -> str:
    """Return ratio as """
    r = precise_ratio(x, y)
    if r == Decimal("100"):
        return "100"
    if r == Decimal("0"):
        return "0"
    return "%.5f" % r

def precise_ratio(x: int, y: int) -> Decimal:
    """Calculate the ratio using more precise decimal rounding.
    This preserves legacy rounding using half-even to 5 decimal places.
    """
    if x == 0 or y == 0:
        return Decimal("0")
    r = 100 * (Decimal(x) / Decimal(y))
    return round_number(r, precision=5, round="nearest")


def round_number(number: Decimal, precision: int=2, round: str="down") -> Decimal:
    """Round decimal number to user defined configurations.
    :param precision: number of decimal places to round to. Can be in range: 0..5
    :param round: rounding strategy for number. Can be one of: ``"down"``, ``"up"``, ``"nearest"``
    """
    quantizer = Decimal("0.1") ** precision
    if round == "up":
        return number.quantize(quantizer, rounding=decimal.ROUND_CEILING)
    if round == "down":
        return number.quantize(quantizer, rounding=decimal.ROUND_FLOOR)
    if round == "nearest":
        return number.quantize(quantizer, rounding=decimal.ROUND_HALF_EVEN)

    log.warning("Rounding scheme is not supported. Defaulting to 'down'.")
    return number.quantize(quantizer, rounding=decimal.ROUND_FLOOR)
