{
    "service": {
        "required": True,
        "type": "dict",
        "schema": {
            "types": {
                "required": True,
                "type": "list",
                "oneof": [
                    {"schema": {"allowed": ["rest", "mqtt"]}},
                    {
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "type": {"allowed": ["rest", "mqtt"]},
                                "port": {"required": False},
                            },
                        }
                    },
                ],
            }
        },
    },
    "devices": {
        "required": True,
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "name": {
                    "required": True,
                    "type": "string",
                },
                "ip": {
                    "required": True,
                    "type": "string",
                    "regex": "^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$",
                },
                "protocol": {
                    "required": True,
                    "type": "string",
                    "allowed": ["http", "coap", "plain_coap"],
                    "oneof": [
                        {"excludes": "poll-timeout", "allowed": ["coap", "plain_coap"]},
                        {"allowed": ["http"]},
                    ],
                },
                "poll-timeout": {
                    "required": False,
                    "type": "integer",
                    "oneof": [{"min": 5}, {"allowed": [0]}],
                },
            },
        },
    },
}