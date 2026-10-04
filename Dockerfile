FROM python:3.14

# node.js for pytubefix PoToken generation
RUN apt-get update && apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./fastapi-ytmp3-working-dir /code/fastapi-ytmp3-working-dir

CMD ["uvicorn", "fastapi-ytmp3-working-dir.ytmp3:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
