FROM python:3.8-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev

RUN pip install pipenv

WORKDIR /app

COPY Pipfile Pipfile.lock /app/

# Install Python dependencies using pipenv
RUN pipenv install --deploy --ignore-pipfile
COPY . /app/

RUN pipenv run python manage.py collectstatic --noinput
RUN pipenv run python manage.py migrate

CMD ["pipenv", "run", "gunicorn", "--bind", "0.0.0.0:8080", "config.wsgi:application"]