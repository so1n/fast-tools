import datetime
from decimal import Decimal

from fast_tools import customer_json as json


class TestCustomerJson:
    def test_customer_json(self) -> None:
        test_dict: dict = {
            "datetime": datetime.datetime.now(),
            "date": datetime.datetime.now().date(),
            "decimal": Decimal("1.01"),
            "time": datetime.time(),
        }
        assert json.loads(json.dumps(test_dict)) == {
            "datetime": test_dict["datetime"].strftime("%Y-%m-%d %H:%M:%S"),
            "date": test_dict["date"].strftime("%Y-%m-%d"),
            "decimal": float(test_dict["decimal"]),
            "time": test_dict["time"].strftime("%H:%M:%S"),
        }
