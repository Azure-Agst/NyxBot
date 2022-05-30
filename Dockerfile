# Base Image
FROM gorialis/discord.py:minimal

# Labels
LABEL org.opencontainers.image.authors="me@azureagst.dev"
LABEL org.opencontainers.image.source="https://github.com/Azure-Agst/NyxBot"

# Set working dir
WORKDIR /usr/src/smbot

# Install Python requirements using pip
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy in rest of app
COPY . .

# Run!
CMD [ "python3", "-m", "nyxbot" ]