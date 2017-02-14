#!/usr/bin/env python
# Copyright 2016 Amazon.com, Inc. or its
# affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not
# use this file except in compliance with the License. A copy of the License is
# located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.
import os
import json
import urllib
import boto3
from PIL import Image
from PIL.ExifTags import TAGS

resized_dir = '/images/resized'
thumb_dir = '/images/thumbs'
input_bucket_name = os.environ['s3InputBucket']
output_bucket_name = os.environ['s3OutputBucket']
sqsqueue_name = os.environ['SQSBatchQueue']
aws_region = os.environ['AWSRegion']
s3 = boto3.client('s3', region_name=aws_region)
sqs = boto3.resource('sqs', region_name=aws_region)


def create_dirs():
    for dirs in [resized_dir, thumb_dir]:
        if not os.path.exists(dirs):
            os.makedirs(dirs)


def process_images():
    """Process the image

    No real error handling in this sample code. In case of error we'll put
    the message back in the queue and make it visable again. It will end up in
    the dead letter queue after five failed attempts.

    """
    for message in get_messages_from_sqs():
        try:
            message_content = json.loads(message.body)
            image = urllib.unquote_plus(message_content
                                        ['Records'][0]['s3']['object']
                                        ['key']).encode('utf-8')
            s3.download_file(input_bucket_name, image, image)
            resize_image(image)
            upload_image(image)
            cleanup_files(image)
        except:
            message.change_visibility(VisibilityTimeout=0)
            continue
        else:
            message.delete()


def cleanup_files(image):
    os.remove(image)
    os.remove(resized_dir + '/' + image)
    os.remove(thumb_dir + '/' + image)


def upload_image(image):
    s3.upload_file(resized_dir + '/' + image,
                   output_bucket_name, 'resized/' + image)
    s3.upload_file(thumb_dir + '/' + image,
                   output_bucket_name, 'thumbs/' + image)


def get_messages_from_sqs():
    results = []
    queue = sqs.get_queue_by_name(QueueName=sqsqueue_name)
    for message in queue.receive_messages(VisibilityTimeout=120,
                                          WaitTimeSeconds=20,
                                          MaxNumberOfMessages=10):
        results.append(message)
    return(results)


def resize_image(image):
    img = Image.open(image)
    exif = img._getexif()
    if exif is not None:
        for tag, value in exif.items():
            decoded = TAGS.get(tag, tag)
            if decoded == 'Orientation':
                if value == 3:
                    img = img.rotate(180)
                if value == 6:
                    img = img.rotate(270)
                if value == 8:
                    img = img.rotate(90)
    img.thumbnail((1024, 768), Image.ANTIALIAS)
    try:
        img.save(resized_dir + '/' + image, 'JPEG', quality=100)
    except IOError as e:
        print("Unable to save resized image")
    img.thumbnail((192, 192), Image.ANTIALIAS)
    try:
        img.save(thumb_dir + '/' + image, 'JPEG')
    except IOError as e:
        print("Unable to save thumbnail")


def main():
    create_dirs()
    while True:
        process_images()


if __name__ == "__main__":
    main()
