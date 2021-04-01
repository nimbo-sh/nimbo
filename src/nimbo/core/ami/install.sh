#!/bin/bash

set -e 

sudo apt-get update
sudo apt install -y build-essential
sudo apt-get install -y linux-headers-$(uname -r)

# Install cuda-11.2
#OS=ubuntu1804
#cudnn_version="8.1.1.*"
#cuda_version="cuda10.2"
#wget https://developer.download.nvidia.com/compute/cuda/repos/${OS}/x86_64/cuda-${OS}.pin
#sudo mv cuda-${OS}.pin /etc/apt/preferences.d/cuda-repository-pin-600
#wget https://developer.download.nvidia.com/compute/cuda/11.0.2/local_installers/cuda-repo-${OS}-11-0-local_11.0.2-450.51.05-1_amd64.deb
#sudo dpkg -i cuda-repo-${OS}-11-0-local_11.0.2-450.51.05-1_amd64.deb
#sudo apt-key add /var/cuda-repo-${OS}-11-0-local/7fa2af80.pub
#sudo apt-get update
#sudo apt-get -y install cuda

#sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/${OS}/x86_64/7fa2af80.pub
#sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/${OS}/x86_64/ /"
#sudo apt-get update
#sudo apt-get install -y libcudnn8=${cudnn_version}-1+${cuda_version}
#sudo apt-get install -y libcudnn8-dev=${cudnn_version}-1+${cuda_version}

#rm cuda-repo-${OS}-11-0-local_11.0.2-450.51.05-1_amd64.deb

# Add NVIDIA package repositories
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/cuda-ubuntu1804.pin
sudo mv cuda-ubuntu1804.pin /etc/apt/preferences.d/cuda-repository-pin-600
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/7fa2af80.pub
sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/ /"
sudo apt-get update

wget http://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64/nvidia-machine-learning-repo-ubuntu1804_1.0.0-1_amd64.deb

sudo apt-get install ./nvidia-machine-learning-repo-ubuntu1804_1.0.0-1_amd64.deb
sudo apt-get update

# Install NVIDIA driver
sudo apt-get install --no-install-recommends nvidia-driver-450
# Reboot. Check that GPUs are visible using the command: nvidia-smi

wget https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64/libnvinfer7_7.1.3-1+cuda11.0_amd64.deb
sudo apt-get install ./libnvinfer7_7.1.3-1+cuda11.0_amd64.deb
sudo apt-get update

# Install development and runtime libraries (~4GB)
sudo apt-get install --no-install-recommends \
    cuda-11-0 \
    libcudnn8=8.0.4.30-1+cuda11.0  \
    libcudnn8-dev=8.0.4.30-1+cuda11.0

echo "export PATH=/usr/local/cuda-11.0/bin${PATH:+:${PATH}}" >> .bashrc
echo "export LD_LIBRARY_PATH=/usr/local/cuda-11.0/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" >> .bashrc

rm libnvinfer7_7.1.3-1+cuda11.0_amd64.deb nvidia-machine-learning-repo-ubuntu1804_1.0.0-1_amd64.deb

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


