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
from prefect import flow, task
from vos import Client
from utils import *


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main():
    """Update the configuration file (config.ini).

    Usage:
        ./task.py config.ini

    """
    client = Client()
    argv = sys.argv[1:]
    if not argv:
        logger.error('Task configuration file not provided. Usage: ./task.py config.ini')
        return 1
    config_file = argv[0]
    if not os.path.exists(config_file):
        raise Exception('Task configuration file does not exist.')

    config = ConfigParser()
    config.read(config_file)
    config = config['sofia-task']
    # Create bash script
    cmd_file_dest = prepare_bash_script(config, client)

    # Submit task
    logger.info('Submitting task')
    params = {
        'name': "sofia-task",
        'image': SOFIA_TASK_IMAGE,
        'cores': 2,
        'ram': 8,
        'kind': "headless",
        'cmd': '/bin/bash', 'args': cmd_file_dest,
        'env': {}
    }
    submit_job(params, logger=logger, interval=1)

    # Fetch log file
    logger.info('Downloading profile log file')
    profile_log = config['profile_log']
    vos_dir = config['vos_dir']
    dest_log_file = os.path.join(vos_dir, profile_log)
    client.copy(vos_path(dest_log_file), profile_log)
    logger.info('Done')
    return

@flow(name="Preparing SoFiA-2 Bash Script")
def prepare_bash_script(config, client):

    # Check task image is available and tagged headless
    check_task_image()

    # Copy sofia parameter file
    params_file_dest = copy_sofia_params(config, client)

    # Copy image file
    image_file_dest = copy_image_file(config, client)

    # Generate bash script
    cmd_file_dest = generate_bash_script(config, client, image_file_dest, params_file_dest)
    return cmd_file_dest

@task
def check_task_image():
    response = canfar_get_images()
    images = [r['id'] for r in response]
    logger.debug(images)
    assert SOFIA_TASK_IMAGE in images, 'SoFiA-2 task image is not in the list of availabe CANFAR headless images'


@task
def copy_sofia_params(config, client):
    parameter_file = config['parameter_file']
    if not os.path.exists(parameter_file):
        raise Exception(f'SoFiA-2 parameter file does not exist')
    parameter_filename = os.path.basename(parameter_file)
    vos_dir = config['vos_dir']
    params_file_dest = os.path.join(vos_dir, parameter_filename)
    client.copy(parameter_file, vos_path(params_file_dest))
    logger.info(f'SoFiA-2 parameter file copied to {params_file_dest}')
    return params_file_dest

@task
def generate_bash_script(config, client, image_file_dest, params_file_dest):
    cmd_file = config['cmd_file']
    logger.info(f'Creating SoFiA-2 run script {cmd_file}')

    vos_dir = config['vos_dir']
    profile_log = os.path.join(vos_dir, config['profile_log'])
    sofia_cmd = f'sofia {params_file_dest} input.data={image_file_dest} output.directory={vos_dir}'
    with open(cmd_file, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write(f'psrecord "{sofia_cmd}" --log {profile_log} --include-io --interval 0.1 --include-children --log-format csv\n')
    cmd_file_dest = os.path.join(vos_dir, cmd_file)
    client.copy(cmd_file, vos_path(cmd_file_dest))
    logger.info(f'SoFiA-2 run script copied to {cmd_file_dest}')
    return cmd_file_dest

@task
def copy_image_file(config, client):
    image_file = config['image_file']
    if not os.path.exists(image_file):
        raise Exception(f'SoFiA-2 target test image cube file does not exist')
    image_filename = os.path.basename(image_file)
    vos_dir = config['vos_dir']
    image_file_dest = os.path.join(vos_dir, image_filename)
    client.copy(image_file, vos_path(image_file_dest))
    logger.info(f'Test SoFiA-2 target image cube file copied to {image_file_dest}')
    return image_file_dest

if __name__ == '__main__':
    main()
