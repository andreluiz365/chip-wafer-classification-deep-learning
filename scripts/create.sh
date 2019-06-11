#!/usr/bin/env bash
# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


templatebucket=$1
templateprefix=$2
stackname=$3
region=$4
SCRIPTDIR=`dirname $0`
if [ "$templatebucket" == "" ]
then
    echo "Usage: $0 <template bucket> <template prefix> <stack name> <region> <--update>"
    exit 1
fi
if [ "$templateprefix" == "" ]
then
    echo "Usage: $0 <template bucket> <template prefix> <stack name> <region> <--update>"
    exit 1
fi
if [ "$stackname" == "" ]
then
    echo "Usage: $0 <template bucket> <template prefix> <stack name> <region> <--update>"
    exit 1
fi
if [ "$region" == "" ]
then
    echo "Usage: $0 <template bucket> <template prefix> <stack name> <region> <--update>"
    exit 1
fi
UPDATE=${5:-""}    
CFN_CMD="create-stack"
if [ "$UPDATE" == "--update" ]
then
    CFN_CMD="update-stack"
    echo "Updating stack"
fi

# Check if we need to append region to S3 URL
TEMPLATE_URL=https://s3.amazonaws.com/$templatebucket/$templateprefix/master.yaml
if [ "$region" != "us-east-1" ]
then
    TEMPLATE_URL=https://s3-$region.amazonaws.com/$templatebucket/$templateprefix/master.yaml
fi

aws s3 sync $SCRIPTDIR/../cfn s3://$templatebucket/$templateprefix

aws cloudformation $CFN_CMD --stack-name $stackname \
    --template-url $TEMPLATE_URL \
    --parameters \
    ParameterKey=TemplateBucketName,ParameterValue=$templatebucket \
    ParameterKey=TemplateBucketPrefix,ParameterValue=$templateprefix \
    --tags Key=Project,Value=ChipWaferAnalysis \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
