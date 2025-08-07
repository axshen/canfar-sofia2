#!/usr/bin/env python3

"""Submit a headless task to CANFAR. There are a bunch of helper functions provided to interact with
SKAHA.

Workflow:

    1. List available headless images
    2. Copy sofia parameter file
    3. Copy image cube
    4. Run headless container
    5. Download logs (profile performance report)

"""

import os
import sys
import logging
from configparser import ConfigParser
from vos import Client
from utils import *


logging.basicConfig(level=logging.INFO)


def main():
    """Update the configuration file (config.ini).

    Usage:
        ./task.py config.ini

    """
    client = Client()
    argv = sys.argv[1:]
    if not argv:
        logging.error('Task configuration file not provided. Usage: ./task.py config.ini')
        return 1
    config_file = argv[0]
    if not os.path.exists(config_file):
        raise Exception('Task configuration file does not exist.')

    config = ConfigParser()
    config.read(config_file)
    config = config['sofia-task']
    vos_dir = config['vos_dir']

    # Check task image is available and tagged headless
    response = canfar_get_images()
    images = [r['id'] for r in response]
    logging.debug(images)
    assert SOFIA_TASK_IMAGE in images, 'SoFiA-2 task image is not in the list of availabe CANFAR headless images'

    # Copy sofia parameter file
    parameter_file = config['parameter_file']
    if not os.path.exists(parameter_file):
        raise Exception(f'SoFiA-2 parameter file does not exist')
    parameter_filename = os.path.basename(parameter_file)
    params_file_dest = os.path.join(vos_dir, parameter_filename)
    client.copy(parameter_file, vos_path(params_file_dest))
    logging.info(f'SoFiA-2 parameter file copied to {params_file_dest}')

    # Copy image file
    image_file = config['image_file']
    if not os.path.exists(image_file):
        raise Exception(f'SoFiA-2 target test image cube file does not exist')
    image_filename = os.path.basename(image_file)
    image_file_dest = os.path.join(vos_dir, image_filename)
    client.copy(image_file, vos_path(image_file_dest))
    logging.info(f'Test SoFiA-2 target image cube file copied to {image_file_dest}')

    # Generate and copy bash script
    cmd_file = config['cmd_file']
    logging.info(f'Creating SoFiA-2 run script {cmd_file}')
    profile_log = os.path.join(vos_dir, config['profile_log'])
    sofia_cmd = f'sofia {params_file_dest} input.data={image_file_dest} output.directory={vos_dir}'
    with open(cmd_file, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write(f'psrecord "{sofia_cmd}" --log {profile_log} --include-io --interval 0.1 --include-children\n')
    cmd_file_dest = os.path.join(vos_dir, cmd_file)
    client.copy(cmd_file, vos_path(cmd_file_dest))
    logging.info(f'SoFiA-2 run script copied to {cmd_file_dest}')

    # Submit task
    logging.info('Submitting task')
    params = {
        'name': "sofia-task",
        'image': SOFIA_TASK_IMAGE,
        'cores': 2,
        'ram': 8,
        'kind': "headless",
        'cmd': '/bin/bash', 'args': cmd_file_dest,
        'env': {}
    }
    submit_job(params, interval=1)

    # Fetch log file
    logging.info('Downloading profile log file')
    profile_log = config['profile_log']
    dest_log_file = os.path.join(vos_dir, profile_log)
    client.copy(vos_path(dest_log_file), profile_log)
    logging.info('Done')
    return


if __name__ == '__main__':
    main()
