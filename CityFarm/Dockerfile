FROM python:3.12-slim

WORKDIR /code
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY code/ /code/
