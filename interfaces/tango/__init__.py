import tango
from badger import interface


class Interface(interface.Interface):

    name = 'tango'

    def __init__(self, params=None):
        super().__init__(params)

    @staticmethod
    def get_default_params():
        return None

    def get_values(self, channels: list):
        vals = {}
        for channel in channels:
            attr = tango.AttributeProxy(channel)
            vals[channel] = attr.read().value
        return vals

    def set_values(self, values: dict):
        for channel, value in values.items():
            attr = tango.AttributeProxy(channel)
            attr.write(value)
