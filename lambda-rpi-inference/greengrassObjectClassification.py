# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import warnings
import time
import greengrasssdk
import os
from threading import Timer
import random
import json
import base64
import io
import mxnet as mx
from mxnet import gluon
from PIL import Image
import numpy as np

client = greengrasssdk.client('iot-data')
model_path = '/greengrass-machine-learning/mxnet/wafers/'
fabid = os.environ['FABID']
cameraid = os.environ['CAMERAID']
interval = int(os.environ['INTERVAL'])
test_files = [os.path.join(dp, f) for dp, dn, fn in os.walk('/volumes/images') for f in fn]
ctx = [mx.cpu()]
synsets = ['Center',
 'Donut',
 'Edge-Loc',
 'Edge-Ring',
 'Loc',
 'Near-full',
 'Random',
 'Scratch',
 'none']

def load_model(mpath):
    print("Loading model")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = gluon.nn.SymbolBlock.imports(
            os.path.join(model_path, "model-symbol.json"), 
            ['data'], 
            os.path.join(model_path, "model-0000.params"), 
            ctx=ctx)

    return model

def predict(net, data):
    print("Starting predict method")
    normalize = gluon.data.vision.transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    test_augs = gluon.data.vision.transforms.Compose([
        # gluon.data.vision.transforms.Resize(256),
        # gluon.data.vision.transforms.CenterCrop(224),
        gluon.data.vision.transforms.ToTensor(),
        normalize])
    print("Set up augmentations")
    
    #nda = mx.img.imdecode(data)
    print("Data shape: " + str(data.shape))
    nda = mx.nd.array(data)
    print("NDA shape: " + str(nda.shape))
    img = test_augs(nda)
    print("Image shape: " + str(img.shape))
    img = img.expand_dims(axis=0)                
    img = img.astype('float32') # for gpu context
    print("Image shape: " + str(img.shape))
    
    output = net(img)
    prediction = mx.nd.argmax(output, axis=1)
    response = prediction.asnumpy().tolist()[0]
    return response

# When deployed to a Greengrass core, this code will be executed immediately
# as a long-lived lambda function.  The code will enter the infinite while loop
# below.
def greengrass_object_classification_run(model):
    print("running inference loop")

    test_file = random.choice(test_files)
    print("Running inference on {0}".format(test_file))
    fname = os.path.split(test_file)[1]
    imgid = os.path.splitext(fname)[0] + '_' + str(int(time.time()))

    imgpayload = {}
    imgpayload['imgid'] = imgid 
    imgpayload['timestamp'] = str(int(time.time()))
    imgpayload['fab'] = fabid
    imgpayload['camera'] = cameraid
    print("Payload before image bytes: " + json.dumps(imgpayload))

    with open(test_file, "rb") as imageFile:
        imgpayload['bytes'] = base64.b64encode(imageFile.read())
        print(imgpayload['bytes'])

    topicPath="fabwafer/{0}/{1}/img/{2}".format(fabid, cameraid, imgid)
    print("Publishing to topic " + topicPath)
    client.publish(
        topic=topicPath,
        payload=json.dumps(imgpayload)
    )
    print("Published to topic " + topicPath)


    print("Calling inference model")
    im_frame = Image.open(test_file)
    im_frame = im_frame.resize((224,224), resample=Image.BILINEAR)
    imrgb = im_frame.convert("RGB")
    im2arr = np.array(imrgb)
    print("Data passed to model has shape " + str(im2arr.shape))
    response = int(predict(model, im2arr))
    print("Got inference response " + str(response))
    topicPath="fabwafer/{0}/{1}/prediction/{2}".format(fabid, cameraid, imgid)
    predpayload = {}
    predpayload['imgid'] = imgid 
    predpayload['timestamp'] = int(time.time())
    predpayload['fab'] = fabid
    predpayload['camera'] = cameraid
    predpayload['prediction'] = synsets[response]
    predpayload['probability'] = 50.0
    print("Prediction payload: " + json.dumps(predpayload))
    client.publish(
        topic=topicPath,
        payload=json.dumps(predpayload)
    )

    # Asynchronously schedule this function to be run again in 3 seconds
    Timer(interval, greengrass_object_classification_run, args=[model]).start()

# Execute the function above
model = load_model(model_path)
greengrass_object_classification_run(model)

# This is a dummy handler and will not be invoked
# Instead the code above will be executed in an infinite loop for our example
def function_handler(event, context):
    print("Got event {0}".format(str(event)))
