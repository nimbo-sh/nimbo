#!/bin/bash
set -e

cd /home/ubuntu

CONDASH=/home/ubuntu/miniconda3/etc/profile.d/conda.sh
if [ -f "$CONDASH" ]; then
    conda activate nimbo
    conda env update -q --file nimbo-environment.yml
else
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -b -p /home/ubuntu/miniconda3
    rm Miniconda3-latest-Linux-x86_64.sh
    echo "source /home/ubuntu/miniconda3/etc/profile.d/conda.sh" >> .bashrc
    source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
    conda env create -q -n nimbo --file nimbo-environment.yml
    conda activate nimbo
    conda install -q -c conda-forge awscli -y
fi

# Import everything from bucket. At some point the env, code, datasets and results folders should be imported separately
mkdir -p data/datasets
mkdir -p data/results

aws s3 cp s3://nimbo-main-bucket /home/ubuntu
