FROM python:3.6.4-alpine3.7

ADD ./code /code
ADD ./requirements.txt .

RUN pip install -r requirements.txt

WORKDIR /code
