from pyairctrl.coap_client import CoAPAirClient
from pyairctrl.http_client import HTTPAirClient
from pyairctrl.plain_coap_client import PlainCoAPAirClient


class ClientFactory:
    @staticmethod
    def get_client_class(protocol):
        if protocol == "http":
            return HTTPAirClient
        elif protocol == "plain_coap":
            return PlainCoAPAirClient
        elif protocol == "coap":
            return CoAPAirClient

    @staticmethod
    def create(protocol, name, host, debug):
        client = ClientFactory.get_client_class(protocol)
        return client(name, host, debug=debug)