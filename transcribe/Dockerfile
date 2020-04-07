FROM python:2.7

COPY transcribe.py ./

RUN pip install pika requests

CMD [ "python", "./transcribe.py"]
