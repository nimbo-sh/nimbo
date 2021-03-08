#!/bin/bash
set -e

cd /home/ubuntu

wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p /home/ubuntu/miniconda3
rm Miniconda3-latest-Linux-x86_64.sh
echo "source /home/ubuntu/miniconda3/etc/profile.d/conda.sh" >> .bashrc
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda create -y -q -n nimbo python=3.7 
conda activate nimbo
conda env update -q --file nimbo-environment.yml
conda install -q -c conda-forge awscli -y

mkdir -p /home/ubuntu/data/datasets
aws s3 cp --recursive s3://nimbo-main-bucket/data/datasets /home/ubuntu/data/datasets

rm -rf /home/ubuntu/data/datasets