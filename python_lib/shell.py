"""Contains utility functions for working with the shell"""
from contextlib import contextmanager
import datetime
from decimal import Decimal
import json
import pprint
import sys
import time
import traceback


SHELL_CONTROL_SEQUENCES = {
    'BLUE': '\033[34m',
    'LTBLUE': '\033[94m',
    'GREEN': '\033[32m',
    'LTGREEN': '\033[92m',
    'YELLOW': '\033[33m',
    'LTYELLOW': '\033[93m',
    'RED': '\033[31m',
    'LTRED': '\033[91m',
    'CYAN': '\033[36m',
    'LTCYAN': '\033[96m',
    'MAGENTA': '\033[35m',
    'LTMAGENTA': '\033[95m',
    'ENDC': '\033[0m',
    'BOLD': '\033[1m',
    'UNDERLINE': '\033[4m',
}


BLUE = "{BLUE}"
LTBLUE = "{LTBLUE}"
GREEN = "{GREEN}"
LTGREEN = "{LTGREEN}"
YELLOW = "{YELLOW}"
LTYELLOW = "{LTYELLOW}"
RED = "{RED}"
LTRED = "{LTRED}"
CYAN = "{CYAN}"
LTCYAN = "{LTCYAN}"
MAGENTA = "{MAGENTA}"
LTMAGENTA = "{LTMAGENTA}"
ENDC = "{ENDC}"
BOLD = "{BOLD}"
UNDERLINE = "{UNDERLINE}"


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        elif isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
            return str(o)
        return super(JSONEncoder, self).default(o)


def read_json(timeout=0):
    """Read json data from stdin"""
    data = read()
    if data:
        return json.loads(data)


def write_output(writer, *output, **kwargs):
    """Write the output to the writer, used for printing to stdout/stderr"""
    to_print = kwargs.get("sep", " ").join(output) + kwargs.get("end", "\n")
    if isinstance(writer, list):
        writer.append(to_print)
    else:
        writer.write(to_print)
        if kwargs.get("flush"):
            writer.flush()


def write_json(output, end='', raw=False, file=None, flush=False):
    file = file or sys.stdout

    if len(output) == 1:
        output = output[0]

    if raw:
        json.dump(output, file, separators=(',', ':'), cls=JSONEncoder)
    else:
        json.dump(output, file, indent=4, sort_keys=True, cls=JSONEncoder)

    if flush:
        file.flush()

    if end:
        write_output(file, '', end=end, sep='', flush=flush)


def read():
    """Read from stdin"""
    return sys.stdin.read()


def choice(choices, msg='Enter your choice: ', color=True, default=None, **kwargs):
    if isinstance(choices, dict):
        choices_dict = choices
        choices = sorted(choices_dict.keys())
    elif isinstance(choices, (tuple, list)):
        choices_dict = None

    choice_msg = ['']
    validate = []
    for idx, item in enumerate(choices):
        if color:
            choice_msg.append("\t{LTYELLOW}%d{LTMAGENTA}: %s" % (idx, str(item)))
        else:
            choice_msg.append("\t%d: %s" % (idx, str(item)))
        validate.append(str(idx))

    choice_msg.append("")
    if color:
        choice_msg.append("{LTMAGENTA}{BOLD}"+msg+"{ENDC}")
    else:
        choice_msg.append(msg)

    output = ask("\n".join(choice_msg), validate=validate, default=default, color=None, **kwargs)

    if choices_dict:
        key = choices[int(output)]
        return choices_dict[key]
    else:
        return choices[int(output)]


def ask(*args, **kwargs):
    """Ask for input"""
    if not sys.stdin.isatty():
        error("Cannot ask user for input, no tty exists")
        sys.exit(1)

    print_args = list(args)
    print_args.append(kwargs.get("end", "\n"))
    if kwargs["color"]:
        print_args.insert(0, "{" + kwargs["color"] + "}")
        print_args.append(ENDC)

    while True:
        stderr(*print_args, end='', **kwargs)

        in_ = input()
        if in_:
            if not kwargs["validate"]:
                return in_
            if isinstance(kwargs["validate"], (tuple, list)) and in_ in kwargs["validate"]:
                return in_
            if callable(kwargs["validate"]) and kwargs["validate"](in_):
                return in_

        if kwargs["default"] is not None:
            return kwargs["default"]

        if kwargs["error_msg"] is not None:
            error("\n" + kwargs["error_msg"] + "\n")
        else:
            error("\nYou didn't enter a valid choice!\n")

        time.sleep(1)


def pretty(output):
    """Pretty format for shell output"""
    return pprint.pformat(output, indent=2, width=100)


def _shell_format(output, **kwargs):
    """Formats the output for printing to a shell"""
    kwargs.update(SHELL_CONTROL_SEQUENCES)
    for idx, item in enumerate(output):
        try:
            output[idx] = item.format(**kwargs)
        except KeyError:
            pass # Can happen if some item is not in the kwargs dict

    return output


def _convert_print(*args):
    """Convert the given arguments to a string for printing. Concantenate them together"""
    output = []
    for arg in args:
        if not isinstance(arg, str):
            arg = pretty(arg)

        output.append(arg)
    return output


def stdout_to_stderr():
    """Temporarily redirects stdout to stderr. Returns no-arg function to turn it back on."""
    stdout = sys.stdout
    sys.stdout = sys.stderr
    def restore_stdout():
        sys.stdout = stdout
    return restore_stdout


def write_info_output(writer, *output, **kwargs):
    if kwargs.get("json"):
        return write_json(output, **kwargs)

    if not kwargs.get("raw", False):
        output = _convert_print(*output)
    output = _shell_format(output, **kwargs)

    write_output(writer, *output, **kwargs)


def stdout(*output, **kwargs):
    """Print to stdout. Supports colors"""
    write_info_output(sys.stdout, *output, **kwargs)


def stderr(*output, **kwargs):
    """Print to stderr. Supports colors"""
    write_info_output(sys.stderr, *output, **kwargs)


def print_color(color, *output, **kwargs):
    """Print message to stderr in the given color"""
    print_args = list(output)
    print_args.append(ENDC)
    if "file" in kwargs:
        write_output(kwargs["file"], *output, **kwargs)
    else:
        stderr(color, *print_args, **kwargs)


def debug(*output, **kwargs):
    """Print debug message to stderr"""
    print_color(BLUE, *output, **kwargs)


def info(*output, **kwargs):
    """Print info message to stderr"""
    print_color(GREEN, *output, **kwargs)


def warning(*output, **kwargs):
    """Print warning message to stderr"""
    print_color(YELLOW, *output, **kwargs)


def error(*output, **kwargs):
    """Print error message to stderr"""
    print_color(RED, *output, **kwargs)


def exception(*output, **kwargs):
    """Print error message to stderr with last exception info"""
    exc = traceback.format_exc()
    print_args = list(output)
    print_args.append("\nAn exception occurred:\n{exc}".format(exc=exc))
    print_color(RED, *print_args, **kwargs)


def timestamp():
    return int(time.time())


@contextmanager
def elapsed(output, **kwargs):
    """Context Manager that prints to stderr how long a process took"""
    start = timestamp()
    info("Starting: ", output, **kwargs)
    yield
    info("Completed: " + output + " {MAGENTA}(Elapsed Time: {elapsed}s){ENDC}", elapsed=timestamp()-start, **kwargs)


def elapsed_decorator(output):
    """Decorator that prints to stderr how long a process took"""
    def wrapper(fn):
        def wrapped_fn(*args, **kwargs):
            with elapsed(output, **kwargs):
                fn(*args, **kwargs)
        return wrapped_fn
    return wrapper


def print_section(color, *output, **kwargs):
    """Prints a section title header"""
    output = ["\n\n", 60 * "#", "\n", "# "] + list(output) + ["\n", 60 * "#", "\n"]
    print_color(color, *output, end="\n", **kwargs)


def print_table(headers, *table_data, **kwargs):
    if not table_data:
        return

    if isinstance(table_data[0], dict):
        all_data = []
        for d in table_data:
            new_output = []
            for header in headers:
                new_output.append(d[header])
            all_data.append(new_output)
    else:
        all_data = table_data

    print(all_data)
    all_data.insert(0, headers)

    widths = [max(len(d[idx]) for d in all_data) for idx, _ in enumerate(headers)]

    output = []
    for row_idx, data in enumerate(all_data):
        line = []
        pad = "<" if row_idx == 0 else ">"
        for idx, item in enumerate(data):
            print(item)
            print(idx)
            formatter = "{item: " + pad + str(widths[idx]) + "}"
            line.append(formatter.format(item=item))

        output.append("| " + " | ".join(line) + " |")

    write_output(kwargs.get("file", sys.stderr), *output, **kwargs)
