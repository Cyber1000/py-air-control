# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import os
import json
from pyairctrl.base_client import NotSupportedException
import pytest
from pyairctrl.coap_client import CoAPAirClient
from pyairctrl.clientfactory import ClientFactory
from testing.coap_test_server import CoAPTestServer
from testing.coap_resources import SyncResource, ControlResource, StatusResource
from pyairctrl.subset_enum import subsetEnum


class TestCoap:
    @pytest.fixture(scope="class")
    def air_client(self):
        return CoAPAirClient("coap", "127.0.0.1")

    @pytest.fixture(scope="class")
    def air_cli(self):
        return ClientFactory.create("coap", "cli", "127.0.0.1", debug=False)

    @pytest.fixture(scope="class")
    def test_data(self):
        return self._test_data()

    def _test_data(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "data.json"), "r") as json_file:
            return json.load(json_file)

    @pytest.fixture(scope="class")
    def sync_resource(self):
        return SyncResource()

    @pytest.fixture(scope="class")
    def status_resource(self):
        return StatusResource()

    @pytest.fixture(scope="class")
    def control_resource(self):
        return ControlResource()

    @pytest.fixture(autouse=True)
    def set_defaults(self, sync_resource, control_resource, status_resource):
        control_resource.set_data(
            '{"CommandType": "app", "DeviceId": "", "EnduserId": "", "mode": "A"}'
        )
        status_resource.set_dataset("status")
        status_resource.set_encryption_key(sync_resource.encryption_key)
        status_resource.set_render_callback(None)

    @pytest.fixture(scope="class", autouse=True)
    def coap_server(self, sync_resource, status_resource, control_resource):
        server = CoAPTestServer(5683)
        server.add_url_rule("/sys/dev/status", status_resource)
        server.add_url_rule("/sys/dev/control", control_resource)
        server.add_url_rule("/sys/dev/sync", sync_resource)
        server.start()
        yield server
        server.stop()

    def test_initConnection_was_called(self, air_client):
        assert air_client.client_key == SyncResource.SYNC_KEY

    def test_set_values(self, air_client):
        values = {}
        values["mode"] = "A"
        result = air_client.set_values(values)
        assert result

    def test_set_wifi_isnotsupported(self, air_client):
        values = {}
        values["ssid"] = "1234"
        values["password"] = "5678"

        with pytest.raises(NotSupportedException) as excinfo:
            result = air_client.set_values(values, subsetEnum.wifi)

        assert (
            "Setting wifi credentials is currently not supported when using CoAP. Use the app instead."
            in str(excinfo.value)
        )

    def test_key_is_increased(self, control_resource):
        air_client = CoAPAirClient("coap", "127.0.0.1")
        values = {}
        values["mode"] = "A"
        result = air_client.set_values(values)
        assert (
            int(control_resource.encoded_counter, 16)
            == int(SyncResource.SYNC_KEY, 16) + 1
        )

    def test_response_is_cut_off_should_return_error(self, status_resource, capfd):
        air_client = CoAPAirClient("coap", "127.0.0.1")
        status_resource.set_render_callback(self.cutoff_data)
        air_client.get_information()
        result, err = capfd.readouterr()
        assert "Message from device got corrupted" in result

    def cutoff_data(self, data):
        return data[:-8]

    def test_get_information_is_valid(
        self, sync_resource, status_resource, air_client, test_data
    ):
        self.assert_json_data(
            air_client.get_information,
            None,
            "status",
            test_data,
            air_client,
            sync_resource,
            status_resource,
        )

    def test_get_wifi_is_isnotsupported(self, air_client):
        with pytest.raises(NotSupportedException) as excinfo:
            air_client.get_information(subsetEnum.wifi)

        assert (
            "Getting wifi credentials is currently not supported when using CoAP. Use the app instead."
            in str(excinfo.value)
        )

    def test_get_information_longsize_is_valid(
        self, sync_resource, status_resource, air_client, test_data
    ):
        dataset = "status-longsize"
        status_resource.set_dataset(dataset)
        self.assert_json_data(
            air_client.get_information,
            None,
            dataset,
            test_data,
            air_client,
            sync_resource,
            status_resource,
        )

    def test_get_firmware_is_valid(
        self, sync_resource, status_resource, air_client, test_data
    ):
        self.assert_json_data(
            air_client.get_information,
            subsetEnum.firmware,
            "firmware",
            test_data,
            air_client,
            sync_resource,
            status_resource,
        )

    def test_get_filters_is_valid(
        self, sync_resource, status_resource, air_client, test_data
    ):
        self.assert_json_data(
            air_client.get_information,
            subsetEnum.filter,
            "filter",
            test_data,
            air_client,
            sync_resource,
            status_resource,
        )

    def test_get_cli_status_is_valid(
        self, sync_resource, status_resource, air_cli, test_data, capfd
    ):
        self.assert_cli_data(
            air_cli.get_information,
            None,
            "status-cli",
            test_data,
            air_cli,
            capfd,
            sync_resource,
            status_resource,
        )

    def test_get_cli_status_for_AC3858_is_valid(
        self, sync_resource, status_resource, air_cli, test_data, capfd
    ):
        dataset = "status-AC3858"
        status_resource.set_dataset(dataset)
        self.assert_cli_data(
            air_cli.get_information,
            None,
            "{}-cli".format(dataset),
            test_data,
            air_cli,
            capfd,
            sync_resource,
            status_resource,
        )

    def test_get_cli_status_err193_is_valid(
        self, sync_resource, status_resource, air_cli, test_data, capfd
    ):
        dataset = "status-err193"
        status_resource.set_dataset(dataset)
        self.assert_cli_data(
            air_cli.get_information,
            None,
            "{}-cli".format(dataset),
            test_data,
            air_cli,
            capfd,
            sync_resource,
            status_resource,
        )

    def test_get_cli_firmware_is_valid(
        self, sync_resource, status_resource, air_cli, test_data, capfd
    ):
        self.assert_cli_data(
            air_cli.get_information,
            subsetEnum.firmware,
            "firmware-cli",
            test_data,
            air_cli,
            capfd,
            sync_resource,
            status_resource,
        )

    def test_get_cli_filters_is_valid(
        self, sync_resource, status_resource, air_cli, test_data, capfd
    ):
        self.assert_cli_data(
            air_cli.get_information,
            subsetEnum.filter,
            "filter-cli",
            test_data,
            air_cli,
            capfd,
            sync_resource,
            status_resource,
        )

    def assert_json_data(
        self,
        air_func,
        subset,
        dataset,
        test_data,
        air_client,
        sync_resource,
        status_resource,
    ):
        result = air_func(subset)
        data = test_data["coap"][dataset]["output"]
        json_data = json.loads(data)
        assert result == json_data

    def assert_cli_data(
        self,
        air_func,
        subset,
        dataset,
        test_data,
        air_cli,
        capfd,
        sync_resource,
        status_resource,
    ):
        air_func(subset)
        result, err = capfd.readouterr()
        assert result == test_data["coap"][dataset]["output"]
