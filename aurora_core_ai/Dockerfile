# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Install system dependencies for audio and opencv
RUN apt-get update && apt-get install -y \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
COPY aurora_core_ai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Aurora stack into the container
# This includes both surface and subsurface logic
COPY . .

# Set PYTHONPATH to include the current directory
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Expose port for Vertex AI
EXPOSE 8080

# Run main.py when the container launches
# We use gunicorn for production stability
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "120", "aurora_core_ai.main:app"]
