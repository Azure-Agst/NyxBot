# Base Image
FROM python:3

# Labels
LABEL org.opencontainers.image.authors="me@azureagst.dev"
LABEL org.opencontainers.image.source="https://github.com/Azure-Agst/NyxBox"

# Set working dir
WORKDIR /usr/src/smbot

# Install Packages using APT
RUN apt update && apt install -y libffi-dev libnacl-dev libsqlite3-dev ffmpeg

# Install Python requirements using PIP
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy in rest of app
COPY . .

# Run!
CMD [ "python3", "-m", "nyxbot" ]