import os
import json
import time
import logging
import requests


CADC_CERTIFICATE = os.getenv('CADC_CERTIFICATE', f'{os.getenv("HOME")}/.ssl/cadcproxy.pem')
CANFAR_IMAGE_URL = 'https://ws-uv.canfar.net/skaha/v0/image'
CANFAR_SESSION_URL = 'https://ws-uv.canfar.net/skaha/v0/session'
RUNNING_STATES = ['Pending', 'Running', 'Terminating']
COMPLETE_STATES = ['Succeeded']
FAILED_STATES = ['Failed']
SOFIA_TASK_IMAGE = 'images.canfar.net/srcnet/sofia-task:latest'


def submit_job(params, logger=None, interval=10):
    """Job wrapper for CANFAR containers. Blocks program until the completion of the headless
    container. Logs container stdout to terminal.

    """
    completed = False
    session_id = create_canfar_session(params, logger).strip('\n')
    logger.info(f'Session: {session_id}')
    while not completed:
        res = info_canfar_session(session_id, logger=logger, logs=False)
        try:
            status = json.loads(res.text)['status']
        except Exception as e:
            logger.exception(e)
            continue

        completed = status in COMPLETE_STATES
        failed = status in FAILED_STATES
        if failed:
            logs = info_canfar_session(session_id, logs=True)
            logger.error(logs.content)
            raise Exception(f'Job failed {logs.text}')

        time.sleep(interval)
        logger.info(f'Job {session_id} {status}')

    # Logging to stdout
    res = info_canfar_session(session_id, logs=True)
    logger.info(res.text)
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


def create_canfar_session(params, logger):
    r = requests.post(CANFAR_SESSION_URL, data=params, cert=CADC_CERTIFICATE)
    if r.status_code != 200:
        logger.error(r.status_code)
        raise Exception(f'Request failed {r.content}')
    return r.content.decode('utf-8')


def info_canfar_session(id, logger, logs=False):
    url = f'{CANFAR_SESSION_URL}/{id}'
    if logs:
        url = f'{url}?view=logs'
    r = requests.get(url, cert=CADC_CERTIFICATE)
    if r.status_code != 200:
        logger.error(r.status_code)
        logger.error(r.content)
    return r
