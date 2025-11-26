#!/usr/bin/env python3
__doc__ = """\
Queries the thermometer periodically and writes the 'internal temperature' and a timestamp to a CSV file.
This program runs forever. Stop it with Ctrl+C.
"""

import sys
import datetime
import time

import temper # next to this script

def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", metavar="seconds", type=int, default=60, help=
        "How often to sample in seconds. default: %(default)d. minimum 1.")
    parser.add_argument("--output", metavar="log.csv", default="-", help=
        "Path to output log file. default is stdout. Opened in append mode. "
        "See also --time-format and --temp-format options. "
        "Ouptut format is 1 line per sample: <time>,<temp>")
    parser.add_argument("--time-format", choices=["iso", "posix"], default="iso", help=
        "Example in iso format: 2025-11-26T14:53:10Z, example in posix format: 1764168790")
    parser.add_argument("--temp-format", choices=["C", "F", "K"], default="C", help=
        "Celsius or Fahrenheit. default: %(default)s. "
        "Conversion from Celsius may introduce misleading significant figures due to floating point math.")
    parser.add_argument("--device", metavar="hidrawN", help=
        "If there are multiple supported devices, use the one with the given info['devices'][-1]. "
        "Default is to use the only device available and error if there are multiple.")
    args = parser.parse_args()

    if args.interval <= 0: parser.error("--interval must be at least 1 (second)")

    if args.output == "-":
        out_file = sys.stdout
    else:
        out_file = open(args.output, "a")

    if args.time_format == "iso":
        def time_format_fn():
            # Example before: 2025-11-26T14:53:10.835759+00:00
            # We want this:   2025-11-26T14:53:10Z
            return datetime.datetime.now(datetime.timezone.utc).isoformat()[:19] + "Z"
    elif args.time_format == "posix":
        def time_format_fn():
            return str(int(time.time()))
    else: assert False

    if args.temp_format == "C":
        def temp_format_fn(celsius):
            return str(celsius)
    elif args.temp_format == "F":
        def temp_format_fn(celsius):
            return str((celsius + 40) * 9 / 5 - 40)
    elif args.temp_format == "K": # Bonus temp format!
        def temp_format_fn(celsius):
            return str(celsius + 273.15)
    else: assert False

    loop_forever(args.interval, out_file, time_format_fn, temp_format_fn, args.device)

def loop_forever(interval, out_file, time_format_fn, temp_format_fn, device):
    origin_time = time.monotonic()
    while True:
        do_sample(out_file, time_format_fn, temp_format_fn, device)
        now = time.monotonic()
        # example of negative modulus: 3 % -10 == -7
        sleep_time = -(now - origin_time) % -interval
        if sleep_time <= 0: sleep_time = interval
        time.sleep(sleep_time)

already_warned = False
def do_sample(out_file, time_format_fn, temp_format_fn, device):
    global already_warned
    outputs = temper.Temper().read()

    # Check for no devices.
    if len(outputs) == 0:
        if not already_warned:
            print("WARNING: no devices found!", file=sys.stderr)
            already_warned = True
        return
    already_warned = False

    if device != None:
        outputs = [
            info for info in outputs
            if info["devices"][-1] == device
        ]
        if len(outputs) == 0: sys.exit("ERROR: --device does not match any available device!")

    # Check for multiple devices.
    if len(outputs) >= 2:
        if device == None:
            sys.exit("ERROR: multiple devices found! give --device with one of: " + " ".join(info["devices"][-1] for info in outputs))
    [info] = outputs

    celsius = info["internal temperature"]
    out_file.write("{},{}\n".format(
        time_format_fn(),
        temp_format_fn(celsius),
    ))
    out_file.flush()

if __name__ == "__main__":
    main()
