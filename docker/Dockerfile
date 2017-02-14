FROM ubuntu:16.04

RUN apt-get update
RUN apt-get install -y python-pip python-imaging
RUN pip install awscli boto3

ADD GetAndResizeImages.py /

CMD ["/GetAndResizeImages.py"]
