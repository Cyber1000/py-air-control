import yaml
import sys
import signal

from os import path
from pyairctrl.restserver import RestServer
from pyairctrl.clientfactory import ClientFactory
from cerberus import Validator
from flask import abort


class ValidationException(Exception):
    pass


class Service:
    def __init__(self, debug):
        self.SERVICEFILE = "service.yml"
        self.SCHEMA = "pyairctrl/service_schema.py"
        self.__services = []
        self.__clients = {}
        self.__debug = debug

    def start(self):
        if not path.exists(self.SERVICEFILE):
            print("You need to create service.yml in your path")
            sys.exit(1)

        with open(self.SERVICEFILE) as file:
            try:
                service = yaml.safe_load(file)
                if self.__debug:
                    print(
                        "Reading configuration-file: {service}".format(service=service)
                    )
                self._validate_schema(service)
            except Exception as e:
                print(
                    "Found an error within service.yaml, exiting now:\n{exception}".format(
                        exception=e
                    )
                )
                sys.exit(0)
            self._start(service)

    def _validate_schema(self, service):
        schema = eval(open(self.SCHEMA, "r").read())
        v = Validator(schema)
        if not v.validate(service, schema):
            raise ValidationException(
                "Validation error:\n{errors}".format(
                    servicefile=self.SERVICEFILE, errors=v.errors
                )
            )

    def _start(self, service):
        for device in service["devices"]:
            client = ClientFactory.create(
                device["protocol"],
                device["name"],
                device["ip"],
                debug=self.__debug,
                additionalArgs=self._get_additionalArgs(device),
            )
            print(
                "Starting Observation of client: {clientname}".format(
                    clientname=client.name
                )
            )
            client.start_observing()
            self.__clients[client.name.lower()] = client

        for servicetype in service["service"]["types"]:
            currentServicetype = (
                servicetype if not "type" in servicetype else servicetype["type"]
            )
            currentPort = None if not "port" in servicetype else servicetype["port"]

            if currentServicetype == "rest":
                service = self._create_rest_service(currentPort)
            self.__services.append(service)
            # TODO daemon: add mqtt
            print("Starting service: {servicename}".format(servicename=service.name))
            service.start()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.pause()

    def _get_additionalArgs(self, device):
        additionalArgs = device.copy()
        additionalArgs.pop("name", None)
        additionalArgs.pop("ip", None)
        additionalArgs.pop("protocol", None)
        if not additionalArgs:
            additionalArgs = None
        return additionalArgs

    def _create_rest_service(self, port):
        service = RestServer(port=port, debug=self.__debug)
        service.add_url_rule(
            "/get/<device>/<subset>/<value>",
            view_func=self._get_information,
            methods=["GET"],
        )
        service.add_url_rule(
            "/get/<device>/<subset>",
            view_func=self._get_information,
            methods=["GET"],
        )
        return service

    def signal_handler(self, sig, frame):
        for client in self.__clients.values():
            print(
                "Stopping Observation of client: {clientname}".format(
                    clientname=client.name
                )
            )
            client.stop_observing()
        print("Stopping all services")
        sys.exit(0)

    def _get_information(self, device, subset, value=None):
        if self.__debug:
            valueInformation = (
                "value {value}".format(value=value)
                if value is not None
                else "all values"
            )
            print(
                "Searching {valueInformation} in subset {subset} on device {device}".format(
                    device=device, subset=subset, valueInformation=valueInformation
                )
            )

        device = device.lower()
        client = self.__clients[device] if device in self.__clients else None
        if client is None:
            abort(404)

        try:
            info = dict(
                (k.lower(), v) for k, v in client.get_information(subset).items()
            )
        except Exception as e:
            if self.__debug:
                print("Unexpected error: {}".format(e))
            abort(404)

        if not value is None:
            value = value.lower()
            if value in info:
                return info[value]
            else:
                abort(404)
        return info

    # TODO daemon: setter missing