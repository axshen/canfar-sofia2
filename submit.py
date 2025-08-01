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
import json
import time
import logging
import requests
from configparser import ConfigParser
from vos import Client
from skaha.images import Images
from skaha.session import Session


logging.basicConfig(level=logging.INFO)


CADC_CERTIFICATE = os.getenv('CADC_CERTIFICATE', f'{os.getenv("HOME")}/.ssl/cadcproxy.pem')
CANFAR_IMAGE_URL = 'https://ws-uv.canfar.net/skaha/v0/image'
CANFAR_SESSION_URL = 'https://ws-uv.canfar.net/skaha/v0/session'
RUNNING_STATES = ['Pending', 'Running', 'Terminating']
COMPLETE_STATES = ['Succeeded']
FAILED_STATES = ['Failed']
SOFIA_TASK_IMAGE = 'images.canfar.net/srcnet/sofia-task:latest'


def submit_job(params, interval=10):
    """Job wrapper for CANFAR containers. Blocks program until the completion of the headless
    container. Logs container stdout to terminal.

    """
    completed = False
    session_id = create_canfar_session(params).strip('\n')
    logging.info(f'Session: {session_id}')
    while not completed:
        res = info_canfar_session(session_id, logs=False)
        try:
            status = json.loads(res.text)['status']
        except Exception as e:
            logging.exception(e)
            continue

        completed = status in COMPLETE_STATES
        failed = status in FAILED_STATES
        if failed:
            logs = info_canfar_session(session_id, logs=True)
            logging.error(logs.content)
            raise Exception(f'Job failed {logs.text}')

        time.sleep(interval)
        logging.info(f'Job {session_id} {status}')

    # Logging to stdout
    res = info_canfar_session(session_id, logs=True)
    logging.info(res.text)
    return


def vos_path(path):
    """Convert a file path for the CANFAR file system to a VOS project space

    """
    vos_path = path.replace('/arc/', 'arc:')
    return vos_path


def canfar_get_images(type='headless'):
    url = f'{CANFAR_IMAGE_URL}?type={type}'
    r = requests.get(url, cert=CADC_CERTIFICATE)
    return json.loads(r.text)


def create_canfar_session(params):
    r = requests.post(CANFAR_SESSION_URL, data=params, cert=CADC_CERTIFICATE)
    if r.status_code != 200:
        logging.error(r.status_code)
        raise Exception(f'Request failed {r.content}')
    return r.content.decode('utf-8')


def info_canfar_session(id, logs=False):
    url = f'{CANFAR_SESSION_URL}/{id}'
    if logs:
        url = f'{url}?view=logs'
    r = requests.get(url, cert=CADC_CERTIFICATE)
    if r.status_code != 200:
        logging.error(r.status_code)
        logging.error(r.content)
    return r


def main():
    """Update the configuration file (config.ini).

    Usage:
        ./submit.py config.ini

    """
    client = Client()
    argv = sys.argv[1:]
    if not argv:
        logging.error('Task configuration file not provided. Usage: ./submit.py config.ini')
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


if __name__ == '__main__':
    main()
