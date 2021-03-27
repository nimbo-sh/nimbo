#!/bin/bash
set -e

PYTHONUNBUFFERED=TRUE
PROJ_DIR=/home/ubuntu/project
CONFIG=nimbo-config.yml
cd $PROJ_DIR

AWS=/usr/local/bin/aws
CONDA_PATH=/home/ubuntu/miniconda3

DELETE_WHEN_DONE="$(grep 'delete_when_done:' $CONFIG | awk '{print $2}')"

DATASETS_PATH="$(grep 'datasets_path:' $CONFIG | awk '{print $2}')"
RESULTS_PATH="$(grep 'results_path:' $CONFIG | awk '{print $2}')"
BUCKET_NAME="$(grep 'bucket_name:' $CONFIG | awk '{print $2}')"
echo "Datasets path: $DATASETS_PATH"
echo "Results path: $RESULTS_PATH"
echo "Bucket name: $BUCKET_NAME"

CONDASH=$CONDA_PATH/etc/profile.d/conda.sh
ENV_NAME="$(grep 'name:' local_env.yml | awk '{print $2}')"
echo ""
echo "Using conda env: $ENV_NAME"

# Import conda from s3
echo ""
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

# If env doesn't exit
echo "Creating conda environment..."
time conda env create -q --file local_env.yml
conda activate $ENV_NAME

echo "Done."

# Import datasets and results from the bucket
mkdir -p $DATASETS_PATH
mkdir -p $RESULTS_PATH

S3_DATASETS_PATH=s3://$BUCKET_NAME/$DATASETS_PATH
S3_RESULTS_PATH=s3://$BUCKET_NAME/$RESULTS_PATH

INSTANCE_DATASETS_PATH=$PROJ_DIR/$DATASETS_PATH
INSTANCE_RESULTS_PATH=$PROJ_DIR/$RESULTS_PATH

echo ""
echo "Importing datasets from $S3_DATASETS_PATH to $INSTANCE_DATASETS_PATH..."
$AWS s3 cp --quiet --recursive $S3_DATASETS_PATH $DATASETS_PATH
printf "Importing results from $S3_RESULTS_PATH to $INSTANCE_RESULTS_PATH..."
$AWS s3 cp --quiet --recursive $S3_RESULTS_PATH $RESULTS_PATH

echo ""
echo "================================================="
echo ""

if [ "$2" = "_nimbo_launch_and_setup" ]; then
    echo "Setup complete. You can now use 'nimbo ssh <instance-id>' to ssh into this instance."
    exit 0
else
    echo "Running job: ${@:2}"
    ${@:2}
fi

echo ""
echo "Saving results to S3..."
$AWS s3 sync $RESULTS_PATH $S3_RESULTS_PATH

conda deactivate
echo ""
echo "Job finished."

if [ "$DELETE_WHEN_DONE" = "yes" ]; then
    echo "Deleting instance $1..."
    $AWS ec2 terminate-instances --instance-ids "$1"
fi