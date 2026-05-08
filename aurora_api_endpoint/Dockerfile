# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install dependencies
COPY aurora_api_endpoint/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the API logic
COPY aurora_api_endpoint/main.py .

# Expose port for Cloud Run
EXPOSE 8080

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "60", "main:app"]
