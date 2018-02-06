FROM python:2.7

COPY tone_analyser.py swift.py ./

RUN pip install pika requests
RUN pip install wrapt python-keystoneclient python-swiftclient

CMD [ "python", "./tone_analyser.py"]
