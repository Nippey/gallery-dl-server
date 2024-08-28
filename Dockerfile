FROM python:alpine

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
RUN mkdir -p /root/.config/gallery-dl

# Prerequisites to install some packages required for yt-dlp
RUN apk add gcc g++ make libffi-dev openssl-dev git ffmpeg brotli 

COPY requirements.txt /usr/src/app/
RUN pip install --root-user-action ignore --no-cache-dir -r requirements.txt

# Also add yt-dlp and its requirements
RUN pip install --root-user-action ignore -U yt-dlp certifi websockets requests mutagen

COPY . /usr/src/app
COPY gallery-dl.base.conf ~/.config/gallery-dl/config.json.sample

EXPOSE 8080


# Folder where the image files will be saved to
VOLUME ["/usr/src/app/gallery-dl"]
# Folder where the user can provide a custom config.json and cookie files (NOT gallery-dl.cong)
VOLUME ["/root/.config/gallery-dl"]

CMD [ "python3", "./gallery_dl_server.py" ]
