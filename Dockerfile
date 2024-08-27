FROM python:alpine

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Prerequisites to install some packages required for yt-dlp
RUN apk add gcc g++ make libffi-dev openssl-dev git ffmpeg brotli 

COPY requirements.txt /usr/src/app/
RUN pip install --root-user-action ignore --no-cache-dir -r requirements.txt

# Also add yt-dlp and its requirements
RUN pip install --root-user-action ignore -U yt-dlp certifi websockets requests mutagen

COPY . /usr/src/app

EXPOSE 8080

VOLUME ["/usr/src/app/gallery-dl"]

CMD [ "python3", "./gallery_dl_server.py" ]
