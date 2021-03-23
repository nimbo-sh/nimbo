#!/bin/bash

AWS=/usr/local/bin/aws
BUCKET_NAME="$(grep 'bucket_name:' config.yml | awk '{print $2}')"

echo 'Hello World' > empty.txt
$AWS s3 cp --quiet empty.txt s3://$BUCKET_NAME/
$AWS s3 rm --quiet s3://$BUCKET_NAME/empty.txt

$AWS ec2 terminate-instances --instance-ids "$1"