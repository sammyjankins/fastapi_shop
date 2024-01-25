FROM tiangolo/uvicorn-gunicorn:python3.9-alpine3.14

WORKDIR /code

RUN apk update && apk upgrade && \
    apk --no-cache add \
    gcc \
    curl

RUN pip install --upgrade pip

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

ADD . /code/

CMD uvicorn main:app --reload --host 0.0.0.0 --port 8989