import os
import json
import time
import logging
import requests
from skaha.session import Session


CADC_CERTIFICATE = os.getenv('CADC_CERTIFICATE', f'{os.getenv("HOME")}/.ssl/cadcproxy.pem')
CANFAR_IMAGE_URL = 'https://ws-uv.canfar.net/skaha/v0/image'
RUNNING_STATES = ['Pending', 'Running', 'Terminating']
COMPLETE_STATES = ['Succeeded']
FAILED_STATES = ['Failed']
SOFIA_TASK_IMAGE = 'images.canfar.net/srcnet/sofia-task:latest'


def submit_job(params, logger=None, interval=10):
    """Job wrapper for CANFAR containers. Blocks program until the completion of the headless
    container. Logs container stdout to terminal.

    """
    completed = False
    session_id = create_canfar_session(params)
    logger.info(f'Session: {session_id}')
    while not completed:
        res = info_canfar_session(session_id)
        try:
            status = res['status']
        except Exception as e:
            logger.exception(e)
            continue

        completed = status in COMPLETE_STATES
        failed = status in FAILED_STATES
        if failed:
            logs = get_logs_canfar_session(session_id)
            logger.error(logs.content)
            raise Exception(f'Job failed {logs.text}')

        time.sleep(interval)
        logger.info(f'Job {session_id} {status}')

    # Logging to stdout
    res = get_logs_canfar_session(session_id)
    logger.info(res)
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
    session = Session()
    session_ids = session.create(
        name=params.get('name'),
        image=params.get('image'),
        cores=params.get('cores'),
        ram=params.get('ram'),
        kind= params.get('kind', 'headless'),
        cmd=params.get('cmd', '/bin/bash'),
        env=params.get('env', {}),
        args=params.get('args', []),
    )
    return session_ids[0]


def info_canfar_session(id):
    session = Session()
    return session.info(id)[0]

def get_logs_canfar_session(id):
    session = Session()
    logs = session.logs(id)[id]
    return logs
