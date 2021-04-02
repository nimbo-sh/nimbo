#!/bin/bash

conda create -n pytorch1.8.0-cuda11.1 pytorch=1.8.0 cudatoolkit=11.1 -c pytorch -c conda-forge
conda env remove -n pytorch1.8.0-cuda11.1

conda create -n pytorch1.8.0-cuda10.2 pytorch=1.8.0 cudatoolkit=10.2 -c pytorch
conda env remove -n pytorch1.8.0-cuda10.2

conda create -n pytorch1.8.0-cuda10.1 pytorch=1.8.0 cudatoolkit=10.1 -c pytorch
conda env remove -n pytorch1.8.0-cuda10.1