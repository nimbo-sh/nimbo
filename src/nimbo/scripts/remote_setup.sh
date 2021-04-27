#!/bin/bash

trap "kill 0" EXIT
trap 'echo "Job failed."; do_cleanup; exit' ERR
trap 'echo "Received signal to stop."; do_cleanup; exit' SIGQUIT SIGTERM SIGINT

do_cleanup () { 
    echo "Backing up nimbo logs..."
    $AWS s3 cp --quiet $LOCAL_LOG $S3_LOG_PATH

    PERSIST="$(grep 'persist:' $CONFIG | awk '{print $2}')"
    if [ "$PERSIST" = "no" ]; then
        echo "Deleting instance $INSTANCE_ID..."
        $AWS ec2 terminate-instances --instance-ids $INSTANCE_ID >/dev/null
        echo "Done."
    fi
}

PYTHONUNBUFFERED=1

INSTANCE_ID=$1
JOB_CMD=$2

AWS=/usr/local/bin/aws
PROJ_DIR=/home/ubuntu/project
CONDA_PATH=/home/ubuntu/miniconda3
CONDASH=$CONDA_PATH/etc/profile.d/conda.sh

cd $PROJ_DIR

CONFIG=nimbo-config.yml
LOCAL_DATASETS_PATH="$(grep 'local_datasets_path:' $CONFIG | awk '{print $2}')"
LOCAL_RESULTS_PATH="$(grep 'local_results_path:' $CONFIG | awk '{print $2}')"
S3_DATASETS_PATH="$(grep 's3_datasets_path:' $CONFIG | awk '{print $2}')"
S3_RESULTS_PATH="$(grep 's3_results_path:' $CONFIG | awk '{print $2}')"
ENCRYPTION="$(grep 'encryption:' $CONFIG | awk '{print $2}')"

if [ -z "${ENCRYPTION}" ]; then
    S3CP="$AWS s3 cp"
    S3SYNC="$AWS s3 sync"
else
    S3CP="$AWS s3 cp --sse $ENCRYPTION"
    S3SYNC="$AWS s3 sync --sse $ENCRYPTION"
fi

ENV_FILE=local_env.yml
ENV_NAME="$(grep 'name:' $ENV_FILE | awk '{print $2}')"

S3_LOG_NAME=$(date +%Y-%m-%d_%H-%M-%S).txt
S3_LOG_PATH=$S3_RESULTS_PATH/nimbo-logs/$S3_LOG_NAME
LOCAL_LOG=/home/ubuntu/nimbo-log.txt
echo "Will save logs to $S3_LOG_PATH"

while true; do 
    $S3CP --quiet $LOCAL_LOG $S3_LOG_PATH > /dev/null 2>&1
    $S3SYNC --quiet $LOCAL_RESULTS_PATH $S3_RESULTS_PATH > /dev/null 2>&1
    sleep 5
done &

mkdir -p $LOCAL_DATASETS_PATH
mkdir -p $LOCAL_RESULTS_PATH

mkdir -p $CONDA_PATH

# ERROR: This currently doesn't allow for a new unseen env to be passed. Fix this.
if [ -f "$CONDASH" ]; then
    echo ""
    echo "Conda installation found."
else
    echo "Conda installation not found. Installing..."
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -bfp /home/ubuntu/miniconda3
    rm Miniconda3-latest-Linux-x86_64.sh
    echo "source $CONDASH" >> .bashrc
fi

source $CONDASH

echo "Creating conda environment: $ENV_NAME"
conda env create -q --file $ENV_FILE
conda activate $ENV_NAME

echo "Done."

# Import datasets and results from the bucket
echo ""
echo "Importing datasets from $S3_DATASETS_PATH to $LOCAL_DATASETS_PATH..."
$S3CP --recursive $S3_DATASETS_PATH $LOCAL_DATASETS_PATH >/dev/null
echo "Importing results from $S3_RESULTS_PATH to $LOCAL_RESULTS_PATH..."
$S3CP --recursive $S3_RESULTS_PATH $LOCAL_RESULTS_PATH >/dev/null

echo ""
echo "================================================="
echo ""

if [ "$JOB_CMD" = "_nimbo_launch_and_setup" ]; then
    echo "Setup complete. You can now use 'nimbo ssh $1' to ssh into this instance."
    exit 0
else
    echo "Running job: ${@:2}"
    ${@:2}
fi

echo ""
echo "Saving results to S3..."
$S3SYNC $LOCAL_RESULTS_PATH $S3_RESULTS_PATH

conda deactivate
echo ""
echo "Job finished."

do_cleanup; exit

