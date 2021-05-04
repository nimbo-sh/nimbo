#!/bin/bash

trap 'echo "Job failed."; do_cleanup; exit 1' ERR
trap 'echo "Received signal to stop."; do_cleanup; exit 1' SIGQUIT SIGTERM SIGINT

do_cleanup () { 
    echo "Deleting instance $INSTANCE_ID."
    sudo shutdown now >/tmp/nimbo-system-logs
}

INSTANCE_ID=$1

echo "Running test script..."

AWS=/usr/local/bin/aws
CONFIG=nimbo-config.yml
source ./nimbo_vars

if [ -z "${ENCRYPTION}" ]; then
    S3CP="$AWS s3 cp"
else
    S3CP="$AWS s3 cp --sse $ENCRYPTION"
fi

echo 'Hello World' > empty.txt
$S3CP empty.txt $S3_DATASETS_PATH
$AWS s3 rm $S3_DATASETS_PATH/empty.txt
$S3CP empty.txt $S3_RESULTS_PATH
$AWS s3 rm $S3_RESULTS_PATH/empty.txt


printf "The instance profile has the required S3 and EC2 permissions \xE2\x9C\x94\n"

printf "Everything working \xE2\x9C\x94\n"

do_cleanup; exit 0