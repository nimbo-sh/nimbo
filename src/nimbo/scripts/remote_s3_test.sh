#!/bin/bash

trap "kill 0" EXIT
trap 'echo "Job failed."; do_cleanup; exit' ERR
trap 'echo "Received signal to stop."; do_cleanup; exit' SIGQUIT SIGTERM SIGINT

do_cleanup () { 
    echo "Deleting instance $INSTANCE_ID..."
    $AWS ec2 terminate-instances --instance-ids $INSTANCE_ID >/dev/null
    echo "Done."
}

INSTANCE_ID=$1

echo "Running test script..."

AWS=/usr/local/bin/aws
CONFIG=nimbo-config.yml

LOCAL_DATASETS_PATH="$(grep 'local_datasets_path:' $CONFIG | awk '{print $2}')"
LOCAL_RESULTS_PATH="$(grep 'local_results_path:' $CONFIG | awk '{print $2}')"
S3_DATASETS_PATH="$(grep 's3_datasets_path:' $CONFIG | awk '{print $2}')"
S3_RESULTS_PATH="$(grep 's3_results_path:' $CONFIG | awk '{print $2}')"

echo 'Hello World' > empty.txt
$AWS s3 cp empty.txt $S3_DATASETS_PATH
$AWS s3 rm $S3_DATASETS_PATH/empty.txt
$AWS s3 cp empty.txt $S3_RESULTS_PATH
$AWS s3 rm $S3_RESULTS_PATH/empty.txt

do_cleanup; exit