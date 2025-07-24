# Use official Ubuntu base image
FROM ubuntu:24.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies (adjust based on your needs)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && apt-get clean

# Create app directory
WORKDIR /app

# Optionally copy your code (if you want it baked into the image)
COPY . /app

# Example: install Python dependencies if requirements.txt exists
RUN pip3 install -r requirements.txt --break-system-packages && \
    rm -r /app/*

# Set default command
CMD ["python3", "main.py"]
# CMD ["ls"]
