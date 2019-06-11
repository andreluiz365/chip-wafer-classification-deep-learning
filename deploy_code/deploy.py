# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import boto3
import os
import sys
import time

# constants / environment variables
client = boto3.client('sagemaker')
ctime = int(time.time())
endpoint_name = os.environ['ENDPOINT_NAME']
image_name = os.environ['IMAGE_NAME']
role_arn = os.environ['ROLE_ARN']
instance_type = os.environ['INSTANCE_TYPE']
model_name = endpoint_name + "-model" + str(ctime)
cfg_name = endpoint_name + "-cfg" + str(ctime)

# helper methods
def create_endpoint(ename, cfgname):
    client.create_endpoint(
        EndpointName=ename,
        EndpointConfigName=cfgname
    )

def create_endpoint_cfg(cfgname, modelname, instance_type):
    client.create_endpoint_config(
        EndpointConfigName=cfgname,
        ProductionVariants=[
            {
                'VariantName': 'main',
                'ModelName': modelname,
                'InitialInstanceCount': 1,
                'InstanceType': instance_type,
                'InitialVariantWeight': 1.0
            },
        ]
    )

def create_model(modelname, modelimage, modelurl, rolearn):
    client.create_model(
        ModelName=modelname,
        PrimaryContainer={
            'Image': modelimage,
            'ModelDataUrl': modelurl
        },
        ExecutionRoleArn=rolearn
    )


# Read job ID and get model artifact from job
fname = sys.argv[1]
with open(fname, 'r') as fin:
    job_id = fin.readline()
    print("Read job id " + job_id)
response = client.describe_training_job(
    TrainingJobName=job_id
)
artifact_path = response['ModelArtifacts']['S3ModelArtifacts']

# Create a model
create_model(model_name, image_name, artifact_path, role_arn)
print("Created model " + model_name)

# Create endpoint config
create_endpoint_cfg(cfg_name, model_name, instance_type)
print("Created endpoint config " + cfg_name)

# Create or update endpoint
print("Checking on endpoint " + endpoint_name)
e_exists = True
try:
    response = client.describe_endpoint(
        EndpointName=endpoint_name
    )

except:
    print("Endpoint not found, creating")
    e_exists = False

if e_exists:
    response = client.update_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=cfg_name
    )
    print("Updated endpoint")
else:
    create_endpoint(endpoint_name, cfg_name)
    print("Created endpoint")

sys.exit(0)
