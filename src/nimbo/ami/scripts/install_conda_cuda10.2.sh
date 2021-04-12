#!/bin/bash

set -e 

sudo apt-get update
sudo apt install -y build-essential
sudo apt-get install -y linux-headers-$(uname -r)

# Install zip
sudo apt-get install -y zip

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


# Install cudatoolkit 10.2
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/cuda-ubuntu1804.pin
sudo mv cuda-ubuntu1804.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/10.2/Prod/local_installers/cuda-repo-ubuntu1804-10-2-local-10.2.89-440.33.01_1.0-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu1804-10-2-local-10.2.89-440.33.01_1.0-1_amd64.deb
sudo apt-key add /var/cuda-repo-10-2-local-10.2.89-440.33.01/7fa2af80.pub
sudo apt-get update
sudo apt-get -y install cuda

echo "export PATH=/usr/local/cuda-10.2/bin${PATH:+:${PATH}}" >> .bashrc
echo "export LD_LIBRARY_PATH=/usr/local/cuda-10.2/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" >> .bashrc

# Install CuDNN 7 and NCCL 2
wget https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64/nvidia-machine-learning-repo-ubuntu1804_1.0.0-1_amd64.deb
sudo dpkg -i nvidia-machine-learning-repo-ubuntu1804_1.0.0-1_amd64.deb

sudo apt update
sudo apt install -y libcudnn7=7.6.5.32-1+cuda10.2 libcudnn7-dev=7.6.5.32-1+cuda10.2

sudo apt autoremove
sudo apt upgrade

sudo ln -s /usr/lib/x86_64-linux-gnu/libcudnn.so.7 /usr/local/cuda-10.2/lib64/