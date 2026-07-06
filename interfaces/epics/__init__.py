import random
import time
from typing import Dict
import warnings
import logging

import numpy as np
from badger import interface
from badger.interface import InterfaceInfo
from badger.errors import BadgerInterfaceChannelError

import epics

epics.ca.DEFAULT_CONNECTION_TIMEOUT = 0.1

logger = logging.getLogger(__name__)

class Interface(interface.Interface):
    name = "epics"
    testing: bool = False

    # list of pv names
    _pv_names: list[str] = []

    @interface.log
    def reset_interface(self):
        epics.ca.clear_cache()

    @interface.log
    def get_info(self, channel_names: list[str]) -> InterfaceInfo:
        result: InterfaceInfo = {
            "vars": {},
            "interface": {"name": self.name, "num_registered_pvs": len(self._pv_names)},
        }

        for channel in channel_names:
            if channel not in self._pv_names:
                self._pv_names.append(channel)

            pv = epics.get_pv(channel)

            pv.wait_for_connection(1)

            result["vars"][channel] = {
                "name": channel,
                "protocol": "CA",
                "connected": str(pv.connected),
                "status": pv.char_status,
                "host": pv.host,
                "access": pv.access,
                "type": pv.type,
            }
        return result

    @interface.log
    def get_bounds(self, channel_names):
        channels = [epics.get_pv(channel) for channel in channel_names]
        low_bounds = [pv.lower_ctrl_limit for pv in channels]
        high_bounds = [pv.upper_ctrl_limit for pv in channels]
        return (low_bounds, high_bounds)

    @interface.log
    def get_values(self, channel_names, as_string: bool = False):
        channel_outputs = {}

        # if testing generate some random numbers and return
        # before starting epics
        if self.testing:
            for channel in channel_names:
                channel_outputs[channel] = random.random()

            return channel_outputs

        for channel in channel_names:
            if channel not in self._pv_names:
                self._pv_names.append(channel)

            pv = epics.get_pv(channel)

            if not pv.wait_for_connection(1):
                raise BadgerInterfaceChannelError(
                    f"failed to connect to epics PV: {channel}"
                )

            count_down = 2  # second
            flag = True
            while count_down > 0:
                logger.debug(f"Trying to get value for PV {channel} (remaining time: {count_down:.1f}s)")
                value = pv.get(as_string=as_string, use_monitor=False, timeout=2)
                if value is None:
                    # Transient CA timeouts can occur; keep retrying until count_down expires.
                    logger.debug(f"CAGET returned None for PV {channel}, retrying")
                    time.sleep(0.1)
                    count_down -= 0.1
                    continue

                if type(value) is str:
                    channel_outputs[channel] = value
                    flag = False
                    break

                try:
                    _ = len(value)
                    value = value[~np.isnan(value)]
                    if len(value):
                        channel_outputs[channel] = value
                        flag = False
                        break
                except Exception:
                    if (value is not None) and (not np.isnan(value)):
                        channel_outputs[channel] = value
                        flag = False
                        break

                time.sleep(0.1)
                count_down -= 0.1

            if flag:
                warnings.warn(f"PV {channel} returned no valid value!")
                channel_outputs[channel] = np.nan

            logger.debug(f"Got value for PV {channel}: {channel_outputs[channel]}")

        return channel_outputs

    @interface.log
    def set_values(self, channel_inputs: Dict) -> Dict:
        channel_outputs = {}

        if self.testing:
            for channel in channel_inputs.keys():
                channel_outputs[channel] = 1.0

            return channel_outputs

        for channel, value in channel_inputs.items():
            logger.debug(f"Setting PV {channel} to value {value}")
            if channel not in self._pv_names:
                self._pv_names.append(channel)
            pv = epics.get_pv(channel)

            if not pv.wait_for_connection(1):
                raise BadgerInterfaceChannelError(
                    f"failed to connect to epics PV: {channel}"
                )

            # Wait for no longer 5s
            pv.put(value, wait=True, timeout=3)
            # The following might not make sense
            # since usually we should set one channel but monitor
            # a corresponding but different channel
            count_down = 2  # second
            flag = True
            while count_down > 0:
                _value = pv.get(timeout=2, use_monitor=False)
                if _value is None:
                    raise Exception(f"CAGET failed for PV {channel}")

                if value:
                    if np.isclose(_value, value, rtol=1e-3):
                        channel_outputs[channel] = _value
                        flag = False
                        break
                else:
                    if np.isclose(_value, value, atol=1e-3):
                        channel_outputs[channel] = _value
                        flag = False
                        break

                time.sleep(0.1)
                count_down -= 0.1

            if flag:
                raise Exception(
                    f"PV {channel} (current: {channel_outputs[channel]}) "
                    + f"cannot reach expected value ({value})!"
                )
            
            logger.debug(f"Successfully set PV {channel} to value {value}")

        return channel_outputs