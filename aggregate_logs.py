#!/usr/bin/env python3

"""Summarise psrecord logs. Reads each log.txt file in a given subdirectory (from the output of parallel.py)
and prints the summary of the entire workflow to stdout. Parsing the log file gives the following info:

Elapsed time, %CPU (avg), Peak Mem (MB), Peak Virtual Mem (MB), CPU-hours

Usage:

    ./aggregate_logs <PATH>

"""

import os
import sys
import glob
import logging
import pandas as pd
import numpy as np


logging.basicConfig(level=logging.INFO)


def parse_logs(logfile):
    """Show runtime and CPU hours for task. Note that we already know the number of cores.

    """
    ncpu = 8
    df = pd.read_csv(logfile)
    avg_cpu = np.mean(df['cpu'])
    runtime = np.max(df['elapsed_time'])
    cpu_hours = avg_cpu * ncpu * runtime / (60*60)
    logging.info('%s: Runtime: %.2fs, avg CPU: %.2f, CPU-hours: %.2f' % (logfile, runtime, avg_cpu, cpu_hours))
    return cpu_hours


def main():
    argv = sys.argv[1:]
    logs_dir = argv[0]
    if not os.path.exists(logs_dir):
        logging.error(f'Provided logs directory does not exist: {logs_dir}')
        sys.exit(1)
    log_files = glob.glob(os.path.join(logs_dir, '*.csv'))
    if not log_files:
        logging.error(f'No log files in provided logs directory {logs_dir}')
        sys.exit(1)
    logging.info(f'Log files: {log_files}')

    # Parse logs
    cpu_hours = 0
    for logfile in log_files:
        cpu_hours += parse_logs(logfile)
    logging.info('Total CPU hours: %.1f' % cpu_hours)


if __name__ == '__main__':
    main()