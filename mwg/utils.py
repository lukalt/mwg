import functools
import re
import json
from io import StringIO


def parse_size(size):
    """
    Parse a formatted byte size string (e.g. 4.1GiB) and returns the number of bytes
    :param size: formatted size
    :return: number of bytes
    """
    units = {"": 1, "b": 1, "kb": 2 ** 10, "mb": 2 ** 20, "gb": 2 ** 30, "tb": 2 ** 40,
             "kib": 10 ** 3, "mib": 10 ** 6, "gib": 10 ** 9, "tib": 10 ** 12}
    matcher = re.match(r'(\d+)([a-zA-Z]{1,3})?', str(size).strip())
    number = float(matcher.group(1))
    unit = matcher.group(2)
    if unit is None:
        return int(number)
    unit = unit.lower()
    if unit not in units:
        raise AttributeError("Malformed size " + size)
    return int(number * units[unit])


def __parse_and_assert(val, parser, assertion, error_message):
    if assertion(parser(val)):
        return
    raise AttributeError(error_message)


def parse_and_assert(parser, assertion, error_message="Assertion failed"):
    return functools.partial(__parse_and_assert, parser=parser, assertion=assertion, error_message=error_message)


class StringBuilder:
    string = None

    def __init__(self):
        self.string = StringIO()

    def Add(self, str):
        self.string.write(str)

    def __str__(self):
        return self.string.getvalue()


def get_number_literal(args, number: int):
    """
    Converts a integer to a literal string of the specified type
    :param args: name of the type to convert the literal to (e.g., `float` or `int`)
    :param number: literal number as an integer
    :return: Number literal as a string
    """
    return str(number) if args.dataType == "int" else str(float(number))


class CustomEncoder(json.JSONEncoder):
    def default(self, z):
        try:
            return super().default(z)
        except TypeError:
            return repr(z)
