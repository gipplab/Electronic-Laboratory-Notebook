"""Component wrappers"""


try:
    from django.core.cache import cache
except:
    class Cache:
        def __init__(self):
            self._cache = {}
        def set(self, key, value):
            self._cache[key] = value
        def get(self, key):
            return self._cache[key]
    cache = Cache()


from .tagging import TaggedInstance
from .CacheValue import CacheValue as CacheValueAutoGen


_NEW_VALUE_PREFIX = "_$_#_NEW:"


class CacheValue(CacheValueAutoGen,
                 TaggedInstance):
    """Overloaded CacheValue component to handle initialisation and server-side argument adjustment.

    An input of 'keyText' or 'value' will provide that argument to the callback, whilst 'keyValue' will
    send the pair.

    An output value of 'keyText' sets that parameter on the component, which is then transferred to the client-side
    keyValue parameter. Outputs of 'value' are not permitted, whilst a 'keyValue' output should contain the
    (key, value) pair; the value is stored in the Cache against the key whilst the key alone is sent to the
    client-side component. 
    """

    def __init__(self, *args, **kwargs):
        print("In CacheValue init")
        print(args)
        print(kwargs)
        key = kwargs.pop('keyText', None)
        value = kwargs.pop('value', None)
        keyValue = kwargs.pop('keyValue', (key, value))
        if keyValue[0] is not None:
            if keyValue[1] is not None:
                kwargs['keyValue'] = f"{_NEW_VALUE_PREFIX}{self.store_value(keyValue)}"
            else:
                kwargs['keyText'] = f"{_NEW_VALUE_PREFIX}{keyValue[0]}"

        print(args)
        print(kwargs)
        super().__init__(*args, **kwargs)

    def store_value(self, keyValue):
        try:
            key, value = keyValue
            if key is not None:
                if value is not None:
                    print(f"STORE: Storing using key {key}")
                    print(f"STORE: Storing value {value}")
                    cache.set(key, value)
            return key
        except Exception as e:
            print("STORE: Store value error as :"+e)
            return keyValue

    def extract_value(self, keyValue):
        """Extract value and form a keyValue pair"""
        print(f"EXTRACT: Extracting value for {keyValue}")
        key = keyValue
        if key is not None:
            value = cache.get(key)
        else:
            value = None
        print(f"EXTRACT: Extracted value is {value}")
        return (key, value)

    def process_input(self, label, value):
        print("INPUT: In process_input")
        print(f"INPUT: LABEL is {label}")
        print(f"INPUT: VALUE is {value}")
        if label == 'keyValue':
            return self.extract_value(value[0])
        if label == 'keyText':
            return self.extract_value(value)[0]

        if label == 'value':
            _, value = self.extract_value(value)

        return value

    def process_output(self, label, value):
        print("OUTPUT: In process_output")
        print(f"OUTPUT: LABEL is {label}")
        print(f"OUTPUT: VALUE is {value}")
        if label == 'keyValue':
            rv = self.store_value(value)
            return rv

        if label == 'value':
            raise ValueError("Cannot return just a Value for a CacheValue component property, use keyValue instead")
        
        if label == 'keyText':
            rv = value
            return rv

        return f"{_NEW_VALUE_PREFIX}{rv}"
