FROM python:3.14

COPY --from=denoland/deno:bin-2.9.7 /deno /usr/local/bin/deno

# node.js for pytubefix PoToken generation
RUN apt-get update && apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*
RUN apt-get update && \
    apt-get install -y ffmpeg --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./fastapi-ytmp3-working-dir /code/fastapi-ytmp3-working-dir