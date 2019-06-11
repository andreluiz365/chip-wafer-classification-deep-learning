# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from sagemaker import get_execution_role
from sagemaker.estimator import Estimator
import os
import sys

output_fname = sys.argv[1]
noop = sys.argv[2]

instance_type = os.environ['INSTANCE_TYPE']
role = os.environ['SAGEMAKER_ROLE_ARN']
region = os.environ['AWS_DEFAULT_REGION']
img_name = os.environ['IMAGE_REPO_NAME']
img_label = os.environ['IMAGE_TAG']
input_path = os.environ['INPUT_DATA']
region = os.environ['AWS_DEFAULT_REGION']
acct = os.environ['AWS_ACCOUNT_ID']
epochs = int(os.environ['EPOCHS'])
lr = float(os.environ['LR'])
batch_size = int(os.environ['BATCH_SIZE'])

print("Instance type = " + instance_type)
print("Epochs = " + str(epochs))
print("LR = " + str(lr))
print("BS = " + str(batch_size))

hyperparameters = {'epochs': epochs, 'lr': lr, 'batch-size': batch_size}

estimator = Estimator(role=role, 
                      train_instance_count=1,
                      train_instance_type=instance_type,
                      image_name="{0}.dkr.ecr.{1}.amazonaws.com/{2}:{3}".format(acct, region, img_name, img_label),
                      metric_definitions=[
                        {'Name': 'valid:loss', 'Regex': 'METRIC_VAL_LOSS=(.*)'},
                        {'Name': 'accuracy', 'Regex': 'METRIC_ACCURACY=(.*)'}
                      ],
                      hyperparameters=hyperparameters)
print("Created estimator, launching job")

if noop == '-n':
    estimator.fit(input_path)
    jobname = estimator._current_job_name
else:
    jobname = noop

print("Saving job name artifact: " + jobname)
with open(output_fname, "w") as fout:
    fout.write(jobname)
