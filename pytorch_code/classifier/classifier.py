# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import ast
import argparse
import requests, io, time
import os
from shutil import copyfile

from fastai.vision import *
from fastai import *
from fastai.callbacks import *

JSON_CONTENT_TYPE = 'application/json'
JPEG_CONTENT_TYPE = 'image/jpeg'
PNG_CONTENT_TYPE = 'image/png'


def _train(args):
    is_distributed = len(args.hosts) > 1 and args.dist_backend is not None
    print("Distributed training - {}".format(is_distributed))

    if is_distributed:
        # Initialize the distributed environment.
        print("Ignoring distributed training")

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print("Device Type: {}".format(device))

    print("Loading dataset")
    DATA = Path(args.data_dir)
    tfms = get_transforms(flip_vert=True, max_lighting = None, max_warp = None)
    data = ImageDataBunch.from_folder(DATA, ds_tfms=tfms, size=224, num_workers=args.workers, bs=args.batch_size)
    print("Model loaded: {0}".format(str(data)))
    learn = create_cnn(data, models.resnet18, metrics=accuracy)

    if torch.cuda.device_count() > 1:
        print("Gpu count: {}".format(torch.cuda.device_count()))

    cb_val_loss = TrackerCallback(learn, monitor='val_loss')
    cb_accuracy = TrackerCallback(learn, monitor='accuracy')
    learn.fit_one_cycle(args.epochs, max_lr=args.lr, callbacks=[cb_val_loss, cb_accuracy])
    accuracy_val = cb_accuracy.get_monitor_value().item()
    loss_val = cb_val_loss.get_monitor_value()

    print('Finished Training')
    print("METRIC_ACCURACY={0}".format(str(accuracy_val)))
    print("METRIC_VAL_LOSS={0}".format(str(loss_val)))
    return _save_model(learn, args.model_dir)


def _save_model(learner, model_dir):
    print("Saving the model.")
    path = Path(os.path.join(model_dir, 'model.pth'))
    epath = Path(os.path.join(model_dir, 'model.pkl'))
    learner.save(path)
    learner.export(epath)


def model_fn(model_dir):
    print('model_fn')
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if torch.cuda.device_count() > 1:
        print("Gpu count: {}".format(torch.cuda.device_count()))

    copyfile(os.path.join(model_dir, 'model.pkl'), '/tmp/export.pkl')
    learn = load_learner(path='/tmp')

    return learn

# Deserialize the Invoke request body into an object we can perform prediction on
def input_fn(request_body, content_type=JPEG_CONTENT_TYPE):
    print('Deserializing the input data.')
    # process an image uploaded to the endpoint
    if content_type == JPEG_CONTENT_TYPE: return open_image(io.BytesIO(request_body))
    if content_type == PNG_CONTENT_TYPE: return open_image(io.BytesIO(request_body))
    # process a URL submitted to the endpoint
    if content_type == JSON_CONTENT_TYPE:
        img_request = requests.get(request_body['url'], stream=True)
        return open_image(io.BytesIO(img_request.content))
    raise Exception('Requested unsupported ContentType in content_type: {}'.format(content_type))

# Perform prediction on the deserialized object, with the loaded model
def predict_fn(input_object, model):
    print("Calling model")
    start_time = time.time()
    predict_class,predict_idx,predict_values = model.predict(input_object)
    print("--- Inference time: %s seconds ---" % (time.time() - start_time))
    print(f'Predicted class is {str(predict_class)}')
    print(f'Predict confidence score is {predict_values[predict_idx.item()].item()}')
    return dict(cls = str(predict_class),
        confidence = predict_values[predict_idx.item()].item())

# Serialize the prediction result into the desired response content type
def output_fn(prediction, accept=JSON_CONTENT_TYPE):        
    print('Serializing the generated output.')
    if accept == JSON_CONTENT_TYPE: return json.dumps(prediction), accept
    raise Exception('Requested unsupported ContentType in Accept: {}'.format(accept))    


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--workers', type=int, default=2, metavar='W',
                        help='number of data loading workers (default: 2)')
    parser.add_argument('--epochs', type=int, default=2, metavar='E',
                        help='number of total epochs to run (default: 2)')
    parser.add_argument('--batch-size', type=int, default=64, metavar='BS',
                        help='batch size (default: 64)')
    parser.add_argument('--lr', type=float, default=0.001, metavar='LR',
                        help='initial learning rate (default: 0.001)')
    parser.add_argument('--momentum', type=float, default=0.9, metavar='M', help='momentum (default: 0.9)')
    parser.add_argument('--dist-backend', type=str, default='gloo', help='distributed backend (default: gloo)')

    # The parameters below retrieve their default values from SageMaker environment variables, which are
    # instantiated by the SageMaker containers framework.
    # https://github.com/aws/sagemaker-containers#how-a-script-is-executed-inside-the-container
    parser.add_argument('--hosts', type=str, default=ast.literal_eval(os.environ['SM_HOSTS']))
    parser.add_argument('--current-host', type=str, default=os.environ['SM_CURRENT_HOST'])
    parser.add_argument('--model-dir', type=str, default=os.environ['SM_MODEL_DIR'])
    parser.add_argument('--data-dir', type=str, default=os.environ['SM_CHANNEL_TRAINING'])
    parser.add_argument('--num-gpus', type=int, default=os.environ['SM_NUM_GPUS'])

    _train(parser.parse_args())
