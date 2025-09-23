import pydoocs
from badger import interface


class Interface(interface.Interface):

    name = 'doocs'

    def __init__(self, params=None):
        super().__init__(params)

    @staticmethod
    def get_default_params():
        return None

    def get_values(self, channels: list):
        val = {}
        for channel in channels:
            val[channel] = pydoocs.read(channel)["data"]

        return val

    def set_values(self, values: dict):
        for channel, value in values.items():
            pydoocs.write(channel, float(value))
