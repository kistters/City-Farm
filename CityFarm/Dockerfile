FROM python:3.6.4-alpine3.7

ADD ./code /code
ADD ./requirements.txt .

RUN pip3 install -r requirements.txt

WORKDIR /code
