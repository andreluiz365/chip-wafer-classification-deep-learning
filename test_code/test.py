# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import boto3
import os
import sys

fname = sys.argv[1]
with open(fname, 'r') as fin:
    job_id = fin.readline()
    print("Read job id " + job_id)

client = boto3.client('sagemaker')

response = client.describe_training_job(
    TrainingJobName=job_id
)

metric_name = os.environ['METRIC_NAME']
metric_threshold = float(os.environ['METRIC_THRESHOLD'])
metric_vals = response['FinalMetricDataList']
fail = 1
for metric_val in metric_vals:
    mname = metric_val['MetricName']
    if mname == metric_name:
        mval = float(metric_val['Value'])
        print("Found the metric of interest: " + metric_name + " = " + str(mval))
        if mval > metric_threshold:
            fail = 0
        break

sys.exit(fail)
