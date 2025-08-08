#!/usr/bin/env python3

"""Run SoFiA-2 on multiple subregions. It is assumed in this workflow that the target data cube is already
copied to the VO space.

Workflow:

    0. Generate sofia parameter files for each subregion
    1. Copy sofia parameter files
    2. Generate bash script for each parameter file
    3. Spawn multiple headless containers
    4. Download logs (profile performance report)

"""

import os
import sys
import glob
import logging
from configparser import ConfigParser
from vos import Client
from concurrent.futures import ProcessPoolExecutor
from utils import *


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main():
    """Update the configuration file (config.ini).

    Usage:
        ./parallel.py config.ini

    """
    client = Client()
    argv = sys.argv[1:]
    if not argv:
        logger.error('Task configuration file not provided. Usage: ./submit.py config.ini')
        return 1
    config_file = argv[0]
    if not os.path.exists(config_file):
        raise Exception('Task configuration file does not exist.')

    config = ConfigParser()
    config.read(config_file)
    config = config['sofia-parallel']
    vos_dir = config['vos_dir']

    # Assert fits image exists
    image_file = config['image_file']
    try:
        client.isfile(vos_path(image_file))
        logger.info(f'Processing image file {image_file}')
    except Exception as e:
        logger.error(f'Image file does not exist in VO space {image_file}')
        sys.exit(1)

    # Check task image is available and tagged headless
    response = canfar_get_images()
    images = [r['id'] for r in response]
    logger.debug(images)
    assert SOFIA_TASK_IMAGE in images, 'SoFiA-2 task image is not in the list of availabe CANFAR headless images'

    # Create list of sofia runs, copy sofia parameter files
    parameter_files = glob.glob(f'{config["parameter_file_dir"]}/*.par')
    logger.info(f'Found the following parameter files: {parameter_files}')
    if not parameter_files:
        raise Exception(f'Parameter files not found')

    run_dict = {}
    logger.info('Copying parameter files to VO space')
    for f in parameter_files:
        basename = os.path.basename(f)
        run_id = os.path.splitext(basename)[0]
        f_dest = os.path.join(vos_dir, basename)
        run_dict[run_id] = {
            'parameter_file_template': f,
            'parameter_file': f_dest
        }
        # client.copy(f, vos_path(f_dest))

    # Update run_dict
    logger.info('Creating scripts to run in each container')
    for run_id, run_config in run_dict.items():
        parameter_file = run_config['parameter_file']
        dirname = os.path.dirname(run_config['parameter_file_template'])
        profile_log = os.path.join(vos_dir, f'{run_id}_profile.txt')
        run_config['profile_log'] = profile_log
        sofia_cmd = f'sofia {parameter_file} input.data={image_file} output.directory={vos_dir}'

        cmd_file = os.path.join(dirname, f'{run_id}_cmd.sh')
        cmd_file_dest = os.path.join(vos_dir, f'{run_id}_cmd.sh')
        with open(cmd_file, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write(f'psrecord "{sofia_cmd}" --log {profile_log} --include-io --interval 0.1 --include-children\n')

        logger.info(f'Copying command file {cmd_file} to VO space')
        # client.copy(cmd_file, vos_path(cmd_file_dest))
        run_config['command'] = cmd_file_dest

    # Run all tasks concurrently
    results = []
    logger.info('Submitting tasks')
    with ProcessPoolExecutor(max_workers=4) as executor:
        for run_id, run_config in run_dict.items():
            name = run_id.replace('_', '-')
            logger.info(f'CANFAR running task {name}')
            params = {
                'name': name,
                'image': SOFIA_TASK_IMAGE,
                'cores': 8,
                'ram': 32,
                'kind': "headless",
                'cmd': '/bin/bash', 'args': run_config['command'],
                'env': {}
            }
            executor.submit(submit_job, params, logger, 1)

    # # Fetch log file
    # logger.info('Downloading profile log file')
    # profile_log = config['profile_log']
    # dest_log_file = os.path.join(vos_dir, profile_log)
    # client.copy(vos_path(dest_log_file), profile_log)
    logger.info('Done')
    return


if __name__ == '__main__':
    main()
