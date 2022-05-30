# Base Image
FROM python:3.9

# Labels
LABEL org.opencontainers.image.authors="me@azureagst.dev"
LABEL org.opencontainers.image.source="https://github.com/Azure-Agst/NyxBot"

# Set working dir
WORKDIR /usr/src/smbot

# Install deps with apt-get
RUN apt-get update && apt-get install -y -qq \
    # - basic deps
    git mercurial cloc openssl ssh gettext sudo build-essential \
    # - voice support
    libffi-dev libsodium-dev libopus-dev ffmpeg

# Update pip, install Cython, pytest, youtube-dl
RUN pip install pip Cython pytest youtube-dl -q --retries 30

# Install Python requirements using pip
ENV SODIUM_INSTALL=system
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy in rest of app
COPY . .

# Run!
CMD [ "python3", "-m", "nyxbot" ]