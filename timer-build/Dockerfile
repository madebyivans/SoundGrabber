# Use a lighter base image
FROM --platform=linux/amd64 python:3.9-slim

# Install Wine and other dependencies
RUN apt-get update && apt-get install -y \
    wine \
    wine32 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /src

# Copy your files
COPY Timer.py .
COPY icon.png .
COPY icon.ico .

# Install Python requirements
RUN pip install --no-cache-dir pyinstaller pyperclip plyer pystray pillow

# Create the exe
RUN pyinstaller --clean --onefile --windowed --icon=icon.ico \
    --add-data "icon.png;." \
    --name Timer \
    Timer.py