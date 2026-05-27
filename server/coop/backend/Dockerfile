FROM python:3.11-slim

WORKDIR /app

# Copy all project files
COPY . /app

# Install python packages
RUN pip install --no-cache-dir flask mysql-connector-python

# Expose the flask port
EXPOSE 5000

# Run flask app
CMD ["python", "app.py"]