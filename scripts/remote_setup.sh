#!/bin/bash
set -e

cd /home/ubuntu

wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p /home/ubuntu/miniconda3
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
export PATH=$PATH:/home/ubuntu/miniconda3/bin
conda create -y -q -n nimbo python=3.7 
conda activate nimbo
conda env update -q --file nimbo-environment.yml
conda install -q -c conda-forge awscli -y
