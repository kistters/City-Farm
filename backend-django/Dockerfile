FROM python:3.8-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIPENV_SYSTEM=1

# Install system dependencies
RUN apk add --no-cache  \
    gcc musl-dev \
    libffi-dev

RUN pip install pipenv

WORKDIR /app

COPY Pipfile Pipfile.lock /app/

# Install Python dependencies using pipenv
RUN pipenv install --deploy --ignore-pipfile
COPY . /app/

EXPOSE 8080
CMD ["daphne", "-b", "0.0.0.0","-p", "8080", "config.asgi:application"]
