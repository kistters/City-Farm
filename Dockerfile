FROM python:3.6.4-alpine3.7

ADD ./code /code

WORKDIR /code

RUN pip3 install -r requirements.txt