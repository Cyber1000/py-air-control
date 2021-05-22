import json
import logging
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict

from coapthon import defines
from coapthon.client.helperclient import HelperClient
from coapthon.messages.request import Request

from pyairctrl.status_transformer import STATUS_TRANSFORMER
from pyairctrl.subset_enum import subsetEnum
from datetime import timezone, datetime


class NotSupportedException(Exception):
    pass


class SetValueException(Exception):
    pass


class TimestampedDict(dict):
    def __init__(self, *args):
        self.__date = {}
        super().__init__(args)

    def __setitem__(self, key, value):
        self.__date[key] = datetime.now(tz=timezone.utc)
        super().__setitem__(key, value)

    def getDateTime(self, key):
        return self.__date[key] if key in self.__date else None


class AirClientBase(ABC):
    def __init__(self, name, host, port, debug=False, additionalArgs=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel("WARN") if debug else self.logger.setLevel("DEBUG")
        self._host = host
        self._port = port
        self._debug = debug
        self.__additionalArgs = additionalArgs
        self.name = name
        self._current_information = TimestampedDict()
        self._isObserving = False
        self._read_ready = threading.Condition(threading.Lock())
        self._readers = 0

    def _get_additionalArg(self, key):
        if self.__additionalArgs and key in self.__additionalArgs:
            return self.__additionalArgs[key]
        return None

    # TODO daemon: change private/protected/public properties
    @classmethod
    def _get_info_for_key(cls, key, raw_value, subset):
        current_value = raw_value
        subsets = None
        name = None
        rawDescription = None
        valueDescription = None

        if key in STATUS_TRANSFORMER:
            instructions = STATUS_TRANSFORMER[key]
            name = instructions["fieldname"]
            subsets = instructions["subsets"]
            rawDescription = instructions["rawDescription"]
            valueDescription = instructions["transformDescription"]

            if not subset is None and subset not in subsets:
                return None

            if not instructions["transform"] is None:
                current_value = instructions["transform"](raw_value)
        else:
            if not subset is None:
                return None

        return {
            "name": name,
            "raw": raw_value,
            "value": current_value,
            "subsets": subsets,
            "rawDescription": rawDescription,
            "valueDescription": valueDescription,
        }

    def _dump_keys(self, current_persistance_dict, subset):
        currentSubset = self._get_persistance_subset(subset)
        if not currentSubset in current_persistance_dict:
            return {}

        current_subset_dict = current_persistance_dict[currentSubset]

        new_current_subset_dict = current_subset_dict.copy()
        for key in current_subset_dict:
            current_value = new_current_subset_dict[key]
            name_and_value = self._get_info_for_key(key, current_value, subset)
            if name_and_value is None:
                new_current_subset_dict.pop(key, None)
                continue

            new_current_subset_dict[key] = name_and_value
            subsetDateTime = self._current_information.getDateTime(currentSubset)
            if subsetDateTime is not None:
                new_current_subset_dict["generalInfo"] = {
                    "unixtimestamp": subsetDateTime.timestamp(),
                    "utctime": str(subsetDateTime),
                }
        return new_current_subset_dict

    def _acquire_read(self):
        self._read_ready.acquire()
        try:
            self._readers += 1
        finally:
            self._read_ready.release()

    def _release_read(self):
        self._read_ready.acquire()
        try:
            self._readers -= 1
            if not self._readers:
                self._read_ready.notifyAll()
        finally:
            self._read_ready.release()

    def _acquire_write(self):
        self._read_ready.acquire()
        while self._readers > 0:
            self._read_ready.wait()

    def _release_write(self):
        self._read_ready.release()

    def get_information(self, subset=None):
        if not self._isObserving:
            self._read_from_device(subset)

        if not any(s for s in subsetEnum if s.name == subset):
            raise NotSupportedException(
                "Enumvalue {value} is not valid in subsetEnum".format(value=subset)
            )

        # TODO wait for first result, may be even in service.py? What if there is an error?
        try:
            self._acquire_read()
            info = self._dump_keys(self._current_information, subset)
            return info
        except Exception as e:
            print("found error: {e}".format(e=e))
        finally:
            self._release_read()
        return {}

    def _get_persistance_subset(self, subset):
        return subset

    @abstractmethod
    def set_values(self, values, subset=None):
        pass

    @classmethod
    @abstractmethod
    def get_devices(cls, timeout=1, repeats=3):
        pass

    @abstractmethod
    def start_observing(self):
        pass

    @abstractmethod
    def stop_observing(self):
        pass

    @abstractmethod
    def _read_from_device(self, subset):
        pass


class CoAPAirClientBase(AirClientBase):
    STATUS_PATH = "/sys/dev/status"
    CONTROL_PATH = "/sys/dev/control"
    SYNC_PATH = "/sys/dev/sync"

    def __init__(self, name, host, port, debug=False, additionalArgs=None):
        super().__init__(name, host, port, debug, additionalArgs)
        self.client = self._create_coap_client()
        self.response = None
        self._initConnection()

    def __del__(self):
        self.stop_observing()

    def start_observing(self):
        self._isObserving = True
        self._read_from_device(None)

    def stop_observing(self):
        if self.client:
            if self.response:
                self.client.cancel_observing(self.response, True)
            self.client.stop()

        self.client = None
        self._isObserving = False

    def _create_coap_client(self):
        return HelperClient(server=(self._host, self._port))

    def get_information(self, subset=None):
        if subset == subsetEnum.wifi:
            raise NotSupportedException(
                "Getting wifi credentials is currently not supported when using CoAP. Use the app instead."
            )
        return super().get_information(subset)

    def _get_persistance_subset(self, subset):
        return subsetEnum.status

    def observecallback(self, response):
        if response:
            payload = self._get_payload(response.payload)
            self._acquire_write()
            subSet = self._get_persistance_subset(None)
            self._current_information[subSet] = payload
            self._release_write()

    def set_values(self, values, subset=None):
        if subset == subsetEnum.wifi:
            raise NotSupportedException(
                "Setting wifi credentials is currently not supported when using CoAP. Use the app instead."
            )

        result = True
        for key in values:
            result = result and self._set(key, values[key])

        return result

    def _read_from_device(self, subset):
        try:
            request = self.client.mk_request(defines.Codes.GET, self.STATUS_PATH)
            request.observe = 0
            observecallback = self.observecallback if self._isObserving else None
            self.response = self.client.send_request(request, observecallback, 2)
            if self.response:
                subset = self._get_persistance_subset(subset)
                self._current_information[subset] = self._get_payload(
                    self.response.payload
                )
        except Exception as e:
            print("Unexpected error:{}".format(e))

    def _get_payload(self, payload):
        try:
            payload = self._transform_payload_after_receiving(payload)
        except Exception as e:
            print("Unexpected error:{}".format(e))

        if payload:
            try:
                return json.loads(payload, object_pairs_hook=OrderedDict)["state"][
                    "reported"
                ]
            except json.decoder.JSONDecodeError:
                print("JSONDecodeError, you may have choosen the wrong coap protocol!")

        return {}

    def _set(self, key, payload):
        try:
            payload = self._transform_payload_before_sending(json.dumps(payload))
            response = self.client.post(self.CONTROL_PATH, payload)

            if self._debug:
                print(response)
            return response.payload == '{"status":"success"}'
        except Exception as e:
            print("Unexpected error:{}".format(e))

    def _send_empty_message(self):
        request = Request()
        request.destination = server = (self._host, self._port)
        request.code = defines.Codes.EMPTY.number
        self.client.send_empty(request)

    @abstractmethod
    def _initConnection(self):
        pass

    @abstractmethod
    def _transform_payload_after_receiving(self, payload):
        pass

    @abstractmethod
    def _transform_payload_before_sending(self, payload):
        pass

    @classmethod
    def get_devices(cls, timeout=1, repeats=3):
        raise NotSupportedException(
            "Autodetection is not supported when using CoAP. Use --ipaddr to set an IP address."
        )