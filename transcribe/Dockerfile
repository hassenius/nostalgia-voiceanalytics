FROM python:2.7

COPY transcribe2.py swift.py ./

RUN pip install pika requests
RUN pip install wrapt python-keystoneclient python-swiftclient

CMD [ "python", "./transcribe2.py"]
