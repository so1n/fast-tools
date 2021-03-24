import datetime
from decimal import Decimal
from fast_tools import customer_json as json


test_dict: dict = {
    "datetime": datetime.datetime.now(),
    "date": datetime.datetime.now().date(),
    "decimal": Decimal('1.01'),
    "time": datetime.time()
}

print(json.dumps(test_dict))
print(json.loads(json.dumps(test_dict)))