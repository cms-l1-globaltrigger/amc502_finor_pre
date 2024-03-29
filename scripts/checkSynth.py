#!/usr/bin/env python
# Created by Philipp Wanggo, Jul 2017
# Extended by Bernhard Arnold, Aug/Dec 2017
#
# Validating synthesis builds.
#

import argparse
import ConfigParser
import logging
import re
import sys, os

from collections import namedtuple

# TTY color sequences
ColorWhiteRed = "\033[37;41;1m"
ColorYellowWhite = "\033[43;37;1m"
ColorReset = "\033[0m"

UtilizationRow = namedtuple('UtilizationRow', 'site_type, used, fixed, available, percent')
"""Tuple holding utilization information."""

# Global message stack
messages = []
utilization = {}

def log_info(message):
    messages.append(message)
    print message

def log_warning(message):
    messages.append(message)
    # Apply TTY colors
    if sys.stdout.isatty():
        message = "{}{}{}".format(ColorYellowWhite, message, ColorReset)
    print message

def log_error(message):
    messages.append(message)
    # Apply TTY colors
    if sys.stdout.isatty():
        message = "{}{}{}".format(ColorWhiteRed, message, ColorReset)
    print message

def log_hr(pattern):
    """Print horizontal line to logger."""
    # TTY size
    o, ts = os.popen('stty size', 'r').read().split()
    log_info(pattern * int(ts))

def parse_utilization(line):
    """Simple parser to read a single row from a utilization report table."""
    cols = [col.strip() for col in line.split("|")][1:-1]
    return UtilizationRow(*cols)

def find_errors(module_path, module_id, args):
    """Parse log files."""

    errors = 0
    warnings = 0
    crit_warnings = 0
    violated_counts = 0

    #
    # Parse Vivado log file
    #

    vivado_log = os.path.join(module_path, 'vivado.log')

    # opens file as .log
    with open(vivado_log) as fp:
        for line in fp:
            line = line.lstrip()
            # checks in current ine if error is at the beginning
            if line.startswith("ERROR"):
                errors += 1
                # checks for args if -a or -e is an arg print error line
                if args.all or args.errors:
                    log_hr("-" )
                    log_info(line)
                    log_hr("-")
            # checks in current ine if warning is at the beginning
            elif line.startswith("WARNING"):
                warnings += 1
                # checks for args if -a or -w is an arg print warning line
                if args.all or args.warnings:
                    log_hr("-")
                    log_info(line)
                    log_hr("-")
            # checks in current ine if critical warning is at the beginning
            elif line.startswith("CRITICAL WARNING"):
                crit_warnings += 1
                # checks for args if -a or -c is an arg print critical warning line
                if args.all or args.criticals:
                    log_hr("-")
                    log_info(line)
                    log_hr("-")

    #
    # Parse timing summary\
    #

    impl_path = os.path.join(module_path, 'top', 'top.runs', 'impl_1')

    # Try to lacate timing summary, first try
    timing_summary = os.path.join(impl_path, 'top_timing_summary_postroute_physopted.rpt')
    if not os.path.isfile(timing_summary):
        # else a second try
        timing_summary = os.path.join(impl_path, 'top_timing_summary_routed.rpt')
        if not os.path.isfile(timing_summary):
            log_error("MISSING TIMING SUMMARY: failed to locate timing summary")
            return

    # Parse timing summary
    with open(timing_summary) as fp:
        while True:
            line = fp.readline()
            # checks if line is empty (EOF)!
            if not line:
                break
            # checks for VIOLATED
            if "VIOLATED" in line:
                # adds 1 to counter if found
                violated_counts += 1
                # checks args for -v and -a
                if args.all or args.violations:
                    log_hr("-")
                    log_info(line.strip(os.linesep))
                    additional_lines = 4
                    for _ in range(additional_lines):
                        log_info(fp.readline().strip(os.linesep))
                    log_hr("-")

    # outputs sum of errors warnings and critical warnings if any accured it gets painted in color
    log_hr("#")

    message = "ERRORS: {}".format(errors)
    log_error(message) if errors else log_info(message)

    message = "WARNINGS: {}".format(warnings)
    log_warning(message) if warnings else log_info(message)

    message = "CRITICAL WARNINGS: {}".format(crit_warnings)
    log_warning(message) if crit_warnings else log_info(message)

    message = "VIOLATED: {}".format(violated_counts)
    log_error(message) if violated_counts else log_info(message)

    #
    # Parse utilization report (dump later)
    #

    utilization_placed = os.path.join(impl_path, 'top_utilization_placed.rpt')

    global utilization
    utilization[module_id] = []

    with open(utilization_placed) as fp:
        for line in fp:
            if line.startswith("| Slice LUTs"):
                utilization[module_id].append(parse_utilization(line))
            if line.startswith("| DSPs"):
                utilization[module_id].append(parse_utilization(line))

    #
    # Check for existing bitfile
    #

    bit_filename = os.path.join(impl_path, 'top.bit')

    if not os.path.isfile(bit_filename):
        log_error("MISSING BIT FILE: {}".format(bit_filename))
        log_info("")
    log_hr("#")

def dump_utilization_report():
    """Dumps utilization summary table."""
    log_info("+--------------------------------------------------------------------+")
    log_info("|                                                                    |")
    log_info("|                     Utilization Design Summary                     |")
    log_info("|                                                                    |")
    log_info("+--------+-----------------------------+-----------------------------+")
    log_info("|        |         Slice LUTs          |            DSPs             |")
    log_info("| Module +------------------+----------+------------------+----------+")
    log_info("|        | Used/Available   | Percent  | Used/Available   | Percent  |")
    log_info("+--------+------------------+----------+------------------+----------+")
    for module_id, utils in utilization.items():
        row = "| {:>6} ".format(module_id)
        for util in utils:
            ratio = "{}/{}".format(util.used, util.available)
            row += "| {:>16} | {:>6} % ".format(ratio, util.percent)
        row += "|"
        log_info(row)
    log_info("+--------+------------------+----------+------------------+----------+")

def parse():
    parser = argparse.ArgumentParser(description="Check synthesis result logs")
    parser.add_argument('config', metavar='config', help="synthesis build configuration file, eg. build_0x10af.cfg")
    parser.add_argument('-m', type=int, metavar='<id>', help="check only a single module ID")
    parser.add_argument('-a', '--all', action='store_true', help="show all errors, warnings, critical warnings and timing violations")
    parser.add_argument('-c', '--criticals', action='store_true', help="show critical warnings")
    parser.add_argument('-e', '--errors', action='store_true', help="show errors")
    parser.add_argument('-w', '--warnings', action='store_true', help="show warnings")
    parser.add_argument('-v', '--violations', action='store_true', help="show timing violations")
    parser.add_argument('-o', metavar='<filename>', help="dumps output to file")
    return parser.parse_args()

def main():
    """Main routine."""

    # Parse command line arguments.
    args = parse()

    # Check for exisiting config file.
    if not os.path.isfile(args.config):
        raise RuntimeError("no such file: {}".format(args.config))

    # Read build configuration.
    config = ConfigParser.ConfigParser()
    config.read(args.config)
    fw_type = config.get('firmware', 'type')
    board_type = config.get('device', 'name')

    build_path = os.path.dirname(args.config)
    #module_path = os.path.join(build_path, menu_name, module_id)
    log_hr("=")
    log_info("{0} {1} synthesis results".format(board_type, fw_type))
    log_hr("=")
    log_info("")
    find_errors(build_path, 0, args)
    log_info("")
        
    dump_utilization_report()
    log_info("")

    if args.o:
        # Write log to file
        with open(os.path.abspath(args.o), 'w+') as fp:
            # Dump accumulated messages
            for message in messages:
                fp.write(message)
                fp.write(os.linesep)


# Run main function with passed arguments.
if __name__ == '__main__':
    sys.exit(main())

#eof
