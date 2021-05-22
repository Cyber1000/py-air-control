import flask

from waitress import serve
from threading import Thread

# TODO daemon: add abstraction level
class RestServer:
    def __init__(self, port, debug=False):
        self.name = "rest"
        self.__flask_server = flask.Flask(__name__)
        self.__port = port if port is not None else 8080
        self.__debug = debug
        self.__thread = Thread(target=self._run, daemon=True)

    def _run(self):
        if self.__debug:
            print("Starting flask-server on port {port}".format(port=self.__port))
        serve(self.__flask_server, host="0.0.0.0", port=self.__port)

    def start(self):
        self.__thread.start()

    def add_url_rule(self, rule, view_func, methods):
        self.__flask_server.add_url_rule(rule, view_func=view_func, methods=methods)
