#!/bin/bash

set -e 

sudo apt-get update
sudo apt install -y build-essential
sudo apt-get install -y linux-headers-$(uname -r)


# Install zip
sudo apt-get install -y zip

# Install texlive
sudo apt-get install -y texlive

# Install awscli-v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm awscliv2.zip
rm -rf ./aws

# Install conda
wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
CONDA_PATH=/home/ubuntu/miniconda3
bash Miniconda3-latest-Linux-x86_64.sh -bfp $CONDA_PATH
CONDASH=$CONDA_PATH/etc/profile.d/conda.sh
echo "source $CONDASH" >> .bashrc
rm Miniconda3-latest-Linux-x86_64.sh

# Install latest nvidia-drivers
distribution=$(. /etc/os-release;echo $ID$VERSION_ID | sed -e 's/\.//g')
wget https://developer.download.nvidia.com/compute/cuda/repos/$distribution/x86_64/cuda-$distribution.pin
sudo mv cuda-$distribution.pin /etc/apt/preferences.d/cuda-repository-pin-600
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/$distribution/x86_64/7fa2af80.pub
echo "deb http://developer.download.nvidia.com/compute/cuda/repos/$distribution/x86_64 /" | sudo tee /etc/apt/sources.list.d/cuda.list
sudo apt-get update
sudo apt-get -y install cuda-drivers



