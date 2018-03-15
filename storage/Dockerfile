FROM python:2.7

COPY rest-service.py swift.py ./

RUN pip install pika requests
RUN pip install Flask python-keystoneclient python-swiftclient

CMD [ "python", "./rest-service.py"]
