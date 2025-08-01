# SoFiA-2 task

A SRCNet Workload task for running [SoFiA-2](https://gitlab.com/SoFiA-Admin/SoFiA-2) on a test dataset with performance profiling. Headlessly executed on CANFAR.

## Setup environment

You will need a bunch of accounts and the correct permissions to run headless tasks on CANFAR. This section describes all of the steps to set up your environment.

* Request a CADC account: https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/auth/request.html
* Install local Python dependencies and utils (`pip install -r requirements.txt`)
* Download the test dataset to the `/arc` storage space

### CADC account

TBA

### Install libraries

```
pip install -r requirements.txt
```

### Authenticate

You need a certificate file to authenticate with CANFAR (and other CADC services)

```
cadc-get-cert -u <USERNAME>
```

### Test dataset

TBA

## Build

We use Docker to build images that run on CANFAR. In this project we have developed a modified SoFiA-2 container with `psutil` and `psrecord` for profiling the execution of SoFiA-2. All scripts requried for this are found in the `image` subdirectory.

To build and push the container from inside the `image` subdirectory

```
docker build --platform linux/amd64 -t images.canfar.net/srcnet/sofia-task:latest .
docker push images.canfar.net/srcnet/sofia-task:latest
```

To tag the image as headless head to the Harbor srcnet repository page: https://images.canfar.net/harbor/projects/27/repositories

Select the image `sofia-task` checkbox, and then under actions click "Add Labels" and then "headless". You should see the table entry update and the headless tag will appear on under the "Labels" column. Now you will be able to submit this job.

**NOTE**: If you rebuild and push an image again you will have to re-tag the container as headless.

## Deploy

Before attempting to deploy the test make sure you are authenticated (`cadc-get-cert`).

1. Copy over dataset
2. Update `sofia.par`

### Download test dataset

This test dataset is provided by the SoFiA-2 team. Follow the steps to download it locally and then update the configuration file to select this dataset.

```
wget https://gitlab.com/SoFiA-Admin/SoFiA-2/-/wikis/documents/sofia_test_datacube.tar.gz
tar -xvf sofia_test_datacube.tar.gz
```

## CANFAR

It can be helpful to run an interactive session to check the environment and perform debugging. You can do this in the CANFAR web interface with a notebook session.

## Links

* [CADC](https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/)
* [VO storage](https://www.canfar.net/en/docs/storage/)
* [CANFAR](https://www.canfar.net/en/)
* [Harbor registry](https://images.canfar.net/)
* [SKAHA API](https://ws-uv.canfar.net/skaha/)
