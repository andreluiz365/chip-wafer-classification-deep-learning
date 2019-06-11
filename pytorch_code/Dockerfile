# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# SageMaker PyTorch image
ARG ACCT=520713654638
ARG REGION=us-west-2
ARG FRAMEWORK=pytorch
ARG PYVERSION=py3
ARG DEVICETYPE=gpu
ARG FRAMEWORKVERSION=1.0.0
FROM $ACCT.dkr.ecr.$REGION.amazonaws.com/sagemaker-$FRAMEWORK:$FRAMEWORKVERSION-$DEVICETYPE-$PYVERSION

ENV PATH="/opt/ml/code:${PATH}"

# /opt/ml and all subdirectories are utilized by SageMaker, we use the /code subdirectory to store our user code.
COPY /classifier /opt/ml/code

# install FastAI
RUN pip install --upgrade fastai

# this environment variable is used by the SageMaker PyTorch container to determine our user code directory.
ENV SAGEMAKER_SUBMIT_DIRECTORY /opt/ml/code

# this environment variable is used by the SageMaker PyTorch container to determine our program entry point
# for training and serving.
# For more information: https://github.com/aws/sagemaker-pytorch-container
ENV SAGEMAKER_PROGRAM classifier.py
