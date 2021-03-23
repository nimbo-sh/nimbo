#!/bin/bash
set -e

PROJ_DIR=/home/ubuntu/project
cd $PROJ_DIR

AWS=/usr/local/bin/aws
CONDA_PATH=/home/ubuntu/miniconda3

DATASETS_PATH="$(grep 'datasets_path:' config.yml | awk '{print $2}')"
RESULTS_PATH="$(grep 'results_path:' config.yml | awk '{print $2}')"
BUCKET_NAME="$(grep 'bucket_name:' config.yml | awk '{print $2}')"
echo "Datasets path: $DATASETS_PATH"
echo "Results path: $RESULTS_PATH"
echo "Bucket name: $BUCKET_NAME"

CONDASH=$CONDA_PATH/etc/profile.d/conda.sh
ENV_NAME="$(grep 'name:' local_env.yml | awk '{print $2}')"
echo ""
echo "Using conda env: $ENV_NAME"

# Import conda from s3
echo ""
echo "Importing your conda envs from s3..."
mkdir -p $CONDA_PATH
if $AWS s3 ls s3://$BUCKET_NAME/conda-envs.tar; then
    $AWS s3 cp s3://$BUCKET_NAME/conda-envs.tar /home/ubuntu/
    tar -xf /home/ubuntu/conda-envs.tar -C $CONDA_PATH
    rm /home/ubuntu/conda-envs.tar
fi


# ERROR: This currently doesn't allow for a new unseen env to be passed. Fix this.
if [ -f "$CONDASH" ]; then
    echo ""
    echo "Conda installation found."
    #echo "source $CONDASH" >> .bashrc
    source $CONDASH

    if conda activate $ENV_NAME; then
        # If env exists
        echo "Env $ENV_NAME found."
        conda activate $ENV_NAME
        conda env export > existing_env.yml

        # We compare all the lines except the last one, because that one has the conda profiles,
        # which will necessarily be different.
        if cmp -s <(head -n -1 existing_env.yml) <(head -n -1 local_env.yml); then
            echo "Imported env matches existing env. Skipping updates."
            UPDATE_ENV=0
        else
            echo "Imported env doesn't match existing env. Updating env..."
            conda env update -q --file local_env.yml
            UPDATE_ENV=1
        fi
        rm existing_env.yml
    else
        # If env doesn't exit
        echo "Env $ENV_NAME not found. Creating..."
        conda env create --file local_env.yml
        conda activate $ENV_NAME
        UPDATE_ENV=1
    fi;

else
    echo "Conda installation not found. Installing..."
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -bfp /home/ubuntu/miniconda3
    rm Miniconda3-latest-Linux-x86_64.sh
    echo "source $CONDASH" >> .bashrc
    source $CONDASH
    echo "Creating $ENV_NAME env..."
    conda env create -q --file local_env.yml
    conda activate $ENV_NAME
    UPDATE_ENV=1
fi

echo "Conda setup complete."

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
    cd repo
    echo "Running job: $@"
    ${@:2}
    cd ..
fi

echo ""
echo "Saving results to S3..."
$AWS s3 sync $RESULTS_PATH $S3_RESULTS_PATH

# If the local and existing environments are different, update the env on the bucket
if [ $UPDATE_ENV -eq 1 ]; then
    echo ""
    echo "Zipping conda env and saving to bucket..."
    tar -cf /home/ubuntu/conda-envs.tar -C $CONDA_PATH .
    $AWS s3 cp /home/ubuntu/conda-envs.tar s3://$BUCKET_NAME/
fi

conda deactivate
echo ""
echo "Job finished."

#$AWS ec2 terminate-instances --instance-ids "$1"