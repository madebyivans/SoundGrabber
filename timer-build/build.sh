#!/bin/bash

# Ensure icons exist
if [ ! -f "icon.png" ] || [ ! -f "icon.ico" ]; then
    echo "Creating icons..."
    python create_icons.py
fi

# Build the Docker image with platform specification
docker build --platform linux/amd64 -t timer-builder .

# Copy the executable from the container
docker create --name temp timer-builder
docker cp temp:/src/dist/Timer.exe .
docker rm temp

echo "Build complete! Timer.exe has been created."