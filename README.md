# SoFiA-2 task

A SRCNet Workload task for running [SoFiA-2](https://gitlab.com/SoFiA-Admin/SoFiA-2) on a test dataset with performance profiling. Headlessly executed on CANFAR.

## Setup environment

These tests currently run on the [Canadian CANFAR instance](https://www.canfar.net/en/). You will need to create an account and request access to certain services to run these tests. This section describes all of the steps to set up your environment.

* Request a CADC account: https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/auth/request.html
* Request permissions to access the group (TBA) and to run headless containers by emailing: support@canfar.net
* Install local Python dependencies and utils (`pip install -r requirements.txt`)
* Download the test dataset to the `/arc` storage space

There is some documentation to help with running headless containers on CANFAR: https://www.opencadc.org/science-containers/complete/headless/.

### Authenticate

Once you have a CADC account and have installed local Python libraries you can download a certificate file locally, which is used to authenticate with CANFAR:

```
cadc-get-cert -u <USERNAME>
```

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
2. Configure
3. Run `python3 task.py config.ini`

### Download task dataset

This test dataset is provided by the SoFiA-2 team. Follow the steps to download it locally and then update the configuration file to select this dataset.

```
wget https://gitlab.com/SoFiA-Admin/SoFiA-2/-/wikis/documents/sofia_test_datacube.tar.gz
tar -xvf sofia_test_datacube.tar.gz
```

### Configure task

Create or update the `config.ini` file with inputs for this task. A description of the required parameters is provided below

| Parameter | Description |
| --- | --- |
| `vos_dir` | Working directory in the VO space (file system that is accessible by the CANFAR containers) |
| `parameter_file` | SoFiA-2 parameter file to be used in the tests. A suitable default can be downloaded as part of the test dataset that is downloaded above. |
| `image_file` | Local copy of the image cube FITS file that will be copied to the VO storage space and processed as part of these tests |
| `profile_log` | Output plaintext file that will contain the `psrecord` profiling information. |
| `cmd_file` | Filename of the bash file containing the command that will be run inside the CANFAR container. |

Note that when a local file does not exist in the current directory (e.g. `/mnt/shared/data/test.fits`) the base filename will be used when copying the data over to the VO storage space.

The `task.py` script copies the required files from your local filesystem to the VO space (VOS) where they are accessible by CANFAR containers. We will automatically generate the executable file that runs `sofia` monitored by a `psrecord` process. The profile log output is automatically downloaded from VOS.

```
python3 task.py config.ini
```

### Parallel

Provided is a script to run SoFiA-2 in parallel using CANFAR. We will split the execution of the entire data cube into smaller sub-regions, each of which will be processed by a separate headless container. The user is responsible for creating the parameter files for this and placing them on your local machine. We assume the image cube is already available on VO space storage. A description of the configuration required is below

| Parameter | Description |
| --- | --- |
| `vos_dir` | Working directory in the VO space (file system that is accessible by the CANFAR containers) |
| `image_file` | Location of the image cube on the VO space. Note that we will not be copying the file over because it is expected that if running in parallel that it will be a large file |
| `parameter_file_dir` | Directory containing all of the parameter files that will be run. |
| `logs_dir` | Directory where the log files (psrecord output) will be copied to on the local directory. |

To run it:

```
python3 parallel.py config.ini
```

This will produce a list of `psrecord` output files in your specified log directory. We have also included a script `aggregate_logs.py` that will summarise the content of your log files and print to console the runtime, %CPU and total CPU-hours of your separate headless container runs, as well as the total resource requirement of the parallelised SoFiA-2 run. You can run this script with

```
python3 aggregate_logs.py <logs_directory>
```

## CANFAR

It can be helpful to run an interactive session to check the environment and perform debugging. You can do this in the CANFAR web interface with a notebook session.

## Links

* [CADC](https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/)
* [VO storage](https://www.canfar.net/en/docs/storage/)
* [CANFAR](https://www.canfar.net/en/)
* [Harbor registry](https://images.canfar.net/)
* [SKAHA API](https://ws-uv.canfar.net/skaha/)
