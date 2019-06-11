# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from __future__ import print_function

import logging
import mxnet as mx
from mxnet import gluon, autograd, init, nd
from mxnet.gluon import nn, model_zoo
import numpy as np
import json
import time
import os

JSON_CONTENT_TYPE = 'application/json'
JPEG_CONTENT_TYPE = 'image/jpeg'
PNG_CONTENT_TYPE = 'image/png'

logging.basicConfig(level=logging.DEBUG)

# ------------------------------------------------------------ #
# Training methods                                             #
# ------------------------------------------------------------ #


def train(current_host, channel_input_dirs, hyperparameters, hosts, num_gpus):
    # SageMaker passes num_cpus, num_gpus and other args we can use to tailor training to
    # the current container environment, but here we just use simple cpu context.
    ctx = [mx.gpu()] if num_gpus > 0 else [mx.cpu()]

    # retrieve the hyperparameters we set in notebook (with some defaults)
    batch_size = hyperparameters.get('batch_size', 100)
    epochs = hyperparameters.get('epochs', 10)
    learning_rate = hyperparameters.get('learning_rate', 0.1)
    momentum = hyperparameters.get('momentum', 0.9)
    wd = hyperparameters.get('wd', 0.001)
    log_interval = hyperparameters.get('log_interval', 100)

    # load training and validation data
    # we use the gluon.data.vision.MNIST class because of its built in mnist pre-processing logic,
    # but point it at the location where SageMaker placed the data files, so it doesn't download them again.
    training_dir = channel_input_dirs['training']
    valid_dir = channel_input_dirs['validation']
    train_data = get_train_data(training_dir, batch_size)
    val_data = get_val_data(valid_dir, batch_size)

    # define the network
    net = define_network()

    # Collect all parameters from net and its children, then initialize them.
    net.output.initialize(init.Xavier(), ctx=ctx)
    net.output.collect_params().setattr('lr_mult', 10)
    net.collect_params().reset_ctx(ctx)
    
    # Trainer is for updating parameters with gradient.
    if len(hosts) == 1:
        kvstore = 'device' if num_gpus > 0 else 'local'
    else:
        kvstore = 'dist_device_sync' if num_gpus > 0 else 'dist_sync'

    trainer = gluon.Trainer(net.collect_params(), 'adam',
                            {'learning_rate': learning_rate, 'wd': wd},
                            kvstore=kvstore)
    metric = mx.metric.Accuracy()
    loss = gluon.loss.SoftmaxCrossEntropyLoss()

    # shard the training data in case we are doing distributed training. Alternatively to splitting in memory,
    # the data could be pre-split in S3 and use ShardedByS3Key to do distributed training.
    if len(hosts) > 1:
        train_data = [x for x in train_data]
        shard_size = len(train_data) // len(hosts)
        for i, host in enumerate(hosts):
            if host == current_host:
                start = shard_size * i
                end = start + shard_size
                break

        train_data = train_data[start:end]
    
    net.hybridize()
    
    for epoch in range(epochs):
        # reset data iterator and metric at begining of epoch.
        metric.reset()
        btic = time.time()
        for i, (data, label) in enumerate(train_data):
            # Copy data to ctx if necessary
            data = data.as_in_context(ctx[0])
            label = label.as_in_context(ctx[0])
            # Start recording computation graph with record() section.
            # Recorded graphs can then be differentiated with backward.
            with autograd.record():
                output = net(data)
                L = loss(output, label)
                L.backward()
            # take a gradient step with batch_size equal to data.shape[0]
            trainer.step(data.shape[0])
            # update metric at last.
            metric.update([label], [output])

            if i % log_interval == 0 and i > 0:
                name, acc = metric.get()
                print('[Epoch %d Batch %d] Training: %s=%f, %f samples/s' %
                      (epoch, i, name, acc, batch_size / (time.time() - btic)))

            btic = time.time()

        name, acc = metric.get()
        print('[Epoch %d] Training: %s=%f' % (epoch, name, acc))

        name, val_acc = test(ctx, net, val_data)
        print('[Epoch %d] Validation: %s=%f' % (epoch, name, val_acc))

    return net


def save(net, model_dir):
    # save the model
    net.export('%s/model'% model_dir)


def define_network():
    
    pretrained_net = model_zoo.vision.resnet18_v2(pretrained=True)
    net = model_zoo.vision.resnet18_v2(classes=9)
    net.features = pretrained_net.features
    
    return net

def get_train_data(data_dir, batch_size):
    train_imgs = gluon.data.vision.ImageRecordDataset(os.path.join(data_dir, 'train_rec.rec'))
                                                     
    normalize = gluon.data.vision.transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])

    train_augs = gluon.data.vision.transforms.Compose([
        gluon.data.vision.transforms.RandomResizedCrop(224),
        gluon.data.vision.transforms.RandomFlipLeftRight(),
        gluon.data.vision.transforms.RandomFlipTopBottom(),
        gluon.data.vision.transforms.ToTensor(),
        normalize])
    
    train_iter = gluon.data.DataLoader(
        train_imgs.transform_first(train_augs), batch_size, shuffle=True, last_batch='rollover')
    
    return train_iter


def get_val_data(data_dir, batch_size):
    valid_imgs = gluon.data.vision.ImageRecordDataset(os.path.join(data_dir, 'valid_rec.rec'))
    
    normalize = gluon.data.vision.transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    
    valid_augs = gluon.data.vision.transforms.Compose([
        gluon.data.vision.transforms.Resize(256),
        gluon.data.vision.transforms.CenterCrop(224),
        gluon.data.vision.transforms.ToTensor(),
        normalize])
    
    valid_iter = gluon.data.DataLoader(valid_imgs.transform_first(valid_augs), batch_size)
    
    return valid_iter


def test(ctx, net, val_data):
    metric = mx.metric.Accuracy()
    for data, label in val_data:
        data = data.as_in_context(ctx[0])
        label = label.as_in_context(ctx[0])
        output = net(data)
        metric.update([label], [output])
    return metric.get()


# ------------------------------------------------------------ #
# Hosting methods                                              #
# ------------------------------------------------------------ #

def model_fn(model_dir):
    """
    Load the gluon model. Called once when hosting service starts.

    :param: model_dir The directory where model files are stored.
    :return: a model (in this case a Gluon network)
    """
    net = gluon.SymbolBlock.imports(
        '%s/model-symbol.json' % model_dir,
        ['data'],
        '%s/model-0000.params' % model_dir,        
    )
    return net


def transform_fn(net, data, input_content_type, output_content_type):
    """
    Transform a request using the Gluon model. Called once per request.

    :param net: The Gluon model.
    :param data: The request payload.
    :param input_content_type: The request content type.
    :param output_content_type: The (desired) response content type.
    :return: response payload and content type.
    """
    normalize = gluon.data.vision.transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    test_augs = gluon.data.vision.transforms.Compose([
        gluon.data.vision.transforms.Resize(256),
        gluon.data.vision.transforms.CenterCrop(224),
        gluon.data.vision.transforms.ToTensor(),
        normalize])
    
    if input_content_type == JPEG_CONTENT_TYPE: 
        nda = mx.img.imdecode(data)
    if input_content_type == PNG_CONTENT_TYPE: 
        nda = mx.img.imdecode(data)
    if input_content_type == JSON_CONTENT_TYPE:
        parsed = json.loads(data)
        nda = mx.nd.array(parsed)
       
    img = test_augs(nda)
    img = img.expand_dims(axis=0)                
    
    output = net(img)
    prediction = mx.nd.argmax(output, axis=1)
    response_body = json.dumps(prediction.asnumpy().tolist()[0])
    return response_body, output_content_type
