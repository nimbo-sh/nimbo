#!/bin/bash
set -e

cd /home/ubuntu

echo "$NEW_VOLUME"
CONDA_PATH=/home/ubuntu/miniconda3

if [ "$NEW_VOLUME" -eq 1 ]; then
    echo "mkfs -t xfs /dev/xvdf"
    sudo mkfs -t xfs /dev/xvdf
fi

mkdir -p $CONDA_PATH

if grep -qs "$CONDA_PATH " /proc/mounts; then
    echo "$CONDA_PATH already mounted."
else
    echo "$CONDA_PATH not mounted. Mounting /dev/xvdf..."
    sudo mount /dev/xvdf $CONDA_PATH
fi
sudo chmod 777 $CONDA_PATH

#sudo apt-get -qq update
#sudo apt-get -qq install awscli -y

CONDASH=$CONDA_PATH/etc/profile.d/conda.sh
ENV_NAME="$(grep 'name:' nimbo-environment.yml | awk '{print $2}')"
echo "Using conda env $ENV_NAME"

if [ -f "$CONDASH" ]; then
    echo "source $CONDASH" >> .bashrc
    source $CONDASH
    conda activate $ENV_NAME
    conda env update -q --file nimbo-environment.yml
else
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -bfp /home/ubuntu/miniconda3
    rm Miniconda3-latest-Linux-x86_64.sh
    echo "source $CONDASH" >> .bashrc
    source $CONDASH
    conda env create -q --file nimbo-environment.yml
    conda activate $ENV_NAME
    #conda install -q -c conda-forge awscli -y
fi
echo "Conda setup complete."

DATASETS_PATH="$(grep 'datasets_path:' config.yml | awk '{print $2}')"
RESULTS_PATH="$(grep 'results_path:' config.yml | awk '{print $2}')"
BUCKET_NAME="$(grep 'bucket_name:' config.yml | awk '{print $2}')"
echo "Datasets path: $DATASETS_PATH"
echo "Results path: $RESULTS_PATH"
echo "Bucket name: $BUCKET_NAME"

# Import datasets and results from the bucket
mkdir -p $DATASETS_PATH
mkdir -p $RESULTS_PATH

S3_DATASETS_PATH=s3://$BUCKET_NAME/$DATASETS_PATH
S3_RESULTS_PATH=s3://$BUCKET_NAME/$RESULTS_PATH

echo "Importing datasets from $S3_DATASETS_PATH"
aws s3 cp --recursive $S3_DATASETS_PATH $DATASETS_PATH
echo "Importing results from $S3_RESULTS_PATH"
aws s3 cp --recursive $S3_RESULTS_PATH $RESULTS_PATH

conda deactivate