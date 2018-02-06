FROM python:2.7

COPY transcribe.py swift.py ./

RUN pip install pika requests
RUN pip install wrapt python-keystoneclient python-swiftclient

CMD [ "python", "./transcribe.py"]
