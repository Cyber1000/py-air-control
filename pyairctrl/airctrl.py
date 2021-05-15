#!/usr/bin/env python3

import argparse
from pyairctrl.cli import Cli


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ipaddr", help="IP address of air purifier")
    parser.add_argument(
        "--protocol",
        help="set the communication protocol",
        choices=["http", "coap", "plain_coap"],
        default="http",
    )
    parser.add_argument("-d", "--debug", help="show debug output", action="store_true")
    parser.add_argument(
        "--om", help="set fan speed", choices=["1", "2", "3", "s", "t", "a"]
    )
    parser.add_argument("--pwr", help="power on/off", choices=["0", "1"])
    parser.add_argument(
        "--mode",
        help="set mode",
        choices=["P", "A", "AG", "F", "S", "M", "B", "N", "T", "GT"],
    )
    parser.add_argument(
        "--rhset", help="set target humidity", choices=["40", "50", "60", "70"]
    )
    parser.add_argument("--func", help="set function", choices=["P", "PH"])
    parser.add_argument(
        "--aqil", help="set light brightness", choices=["0", "25", "50", "75", "100"]
    )
    parser.add_argument("--uil", help="set button lights on/off", choices=["0", "1"])
    parser.add_argument(
        "--ddp",
        help="set indicator IAI/PM2.5/Gas/Humidity",
        choices=["0", "1", "2", "3"],
    )
    parser.add_argument(
        "--dt",
        help="set timer",
        choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
    )
    parser.add_argument("--cl", help="set child lock", choices=["True", "False"])
    parser.add_argument("--wifi", help="read wifi options", action="store_true")
    parser.add_argument("--wifi-ssid", help="set wifi ssid")
    parser.add_argument("--wifi-pwd", help="set wifi password")
    parser.add_argument("--firmware", help="read firmware", action="store_true")
    parser.add_argument("--filters", help="read filters status", action="store_true")
    parser.add_argument(
        "--service", help="start as service - service.yml needed", action="store_true"
    )
    args = parser.parse_args()

    if not args.service:
        Cli.execute(args)


if __name__ == "__main__":
    main()
