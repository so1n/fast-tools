import logging
from datetime import time, date, datetime
from decimal import Decimal
from functools import singledispatch
from typing import Any, Union

try:
    import ojson as json
except ImportError:
    try:
        import ujson as json
    except ImportError:
        import json


@singledispatch
def json_default(obj: Any) -> Any:
    raise TypeError(repr(obj) + " is not JSON serializable")


@json_default.register(datetime)
def _datetime(obj: Any) -> str:
    return obj.strftime('%Y-%m-%d %H:%M:%S')


@json_default.register(date)
def _date(obj: Any) -> str:
    return obj.strftime('%Y-%m-%d')


@json_default.register(time)
def _time(obj: Any) -> str:
    return obj.strftime('%H:%M:%S')


@json_default.register(Decimal)
def _decimal(obj: Any) -> Union[int, float, str]:
    try:
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    except Exception as exception:
        logging.error("Please solve json problem %s", str(exception))
        return str(obj)


def dumps(obj: Any, **kwargs: Any) -> str:
    """JSON dumps function"""
    return json.dumps(obj, default=json_default, **kwargs)


def loads(json_str: str, **kwargs: Any) -> Any:
    """JSON loads function"""
    return json.loads(json_str, **kwargs)


def test():
    """Test function"""
    testcase = loads('''{"A":["B", "C", {"D":["E", "F"], "I": 123, "J": 321.0,
        "K": null, "L": true}],"M": false, "O": null,
        "P": "2015-12-03 11:11:11"}''')

    print(testcase)

    testcase['Q'] = Decimal('1')
    testcase['R'] = Decimal('1.01')
    testcase['S'] = datetime.now()
    testcase['T'] = Decimal('nan')

    print(dumps(testcase))


if __name__ == '__main__':
    test()
