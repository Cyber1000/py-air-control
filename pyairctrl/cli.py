from logging import debug
import sys
import pprint
import json

from pyairctrl.base_client import NotSupportedException, SetValueException
from pyairctrl.cli_format import CLI_FORMAT
from pyairctrl.subset_enum import subsetEnum
from pyairctrl.clientfactory import ClientFactory


class Cli:
    def __init__(self, client, debug):
        self._client = client
        self._debug = debug

    @classmethod
    def _format_key_values(cls, status):
        for key in status:
            if "value" not in status[key] or status[key]["value"] is None:
                continue

            name_and_value = cls._get_name_for_key(key, status[key])

            prefix = "[{key}]\t".format(key=key)
            print(
                "{prefix}{name_and_value}".format(
                    prefix=prefix, name_and_value=name_and_value
                ).expandtabs(30)
            )

    @staticmethod
    def _get_name_for_key(key, singleEntry):
        formatter = (
            CLI_FORMAT[key]["format"]
            if key in CLI_FORMAT
            else "{name}: {{}}".format(name=singleEntry["name"])
            if not singleEntry["name"] is None
            else "{name}: {{}}".format(name=key)
        )
        return formatter.format(singleEntry["value"])

    def get_information(self, subset=None):
        try:
            status = self._client.get_information(subset)
            if status is None:
                noneInfo = (
                    "info" if subset is None else "{subset}-info".format(subset=subset)
                )
                print("No {noneInfo} found".format(noneInfo=noneInfo))
                return

            if self._debug:
                print("Raw status:")
                print(json.dumps(status, indent=4))
            self._format_key_values(status)
        except NotSupportedException as e:
            print(e)

    def set_values(self, values, subset=None):
        try:
            if self._debug:
                pprint.pprint(values)
            values = self._client.set_values(values, subset)
        except (NotSupportedException, SetValueException) as e:
            print(e)

    @staticmethod
    def get_devices(protocol, ipaddr, debug):
        if ipaddr:
            return [{"ip": ipaddr}]

        try:
            client = ClientFactory.get_client_class(protocol)
            devices = client.get_devices(debug)
            if debug:
                pprint.pprint(devices)
            if not devices:
                print(
                    "Air purifier not autodetected. Try --ipaddr option to force specific IP address."
                )
                sys.exit(1)
            return devices
        except NotSupportedException as e:
            print(e)
            sys.exit(1)

    @classmethod
    def execute(cls, args):
        devices = cls.get_devices(args.protocol, args.ipaddr, debug=args.debug)
        for device in devices:
            c = cls(
                ClientFactory.create(
                    args.protocol, "cli", device["ip"], debug=args.debug
                ),
                debug=args.debug,
            )

            subset = None
            if args.wifi or args.wifi_ssid or args.wifi_pwd:
                subset = subsetEnum.wifi
            if args.firmware:
                subset = subsetEnum.firmware
            if args.filters:
                subset = subsetEnum.filter

            values = {}
            if args.wifi_ssid:
                values["ssid"] = args.wifi_ssid
            if args.wifi_pwd:
                values["password"] = args.wifi_pwd

            if subset is None:
                if args.om:
                    values["om"] = args.om
                if args.pwr:
                    values["pwr"] = args.pwr
                if args.mode:
                    values["mode"] = args.mode
                if args.rhset:
                    values["rhset"] = int(args.rhset)
                if args.func:
                    values["func"] = args.func
                if args.aqil:
                    values["aqil"] = int(args.aqil)
                if args.ddp:
                    values["ddp"] = args.ddp
                if args.uil:
                    values["uil"] = args.uil
                if args.dt:
                    values["dt"] = int(args.dt)
                if args.cl:
                    values["cl"] = args.cl == "True"

            if values:
                c.set_values(values, subset)

            c.get_information(subset)