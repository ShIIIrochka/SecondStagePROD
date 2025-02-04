FROM python:3.12-alpine

COPY ./pyproject.toml /

RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry self add poetry-plugin-export && \
    poetry export -f requirements.txt -o requirements.txt && \
    pip install -r requirements.txt

COPY . /app
WORKDIR /app

COPY ./entrypoint.sh /
ENTRYPOINT [ "ash", "/entrypoint.sh"]
