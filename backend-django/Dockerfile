FROM python:3.8-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIPENV_SYSTEM=1

# Install system dependencies
RUN apk add --no-cache gcc musl-dev

RUN pip install pipenv

WORKDIR /app

COPY Pipfile Pipfile.lock /app/

# Install Python dependencies using pipenv
RUN pipenv install --deploy --ignore-pipfile
COPY . /app/

RUN python manage.py collectstatic --noinput
RUN python manage.py migrate

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "config.wsgi:application"]