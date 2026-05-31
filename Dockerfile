# Use official slim Python image for small size
FROM python:3.11-slim

WORKDIR /mesh
COPY ./ /mesh
RUN ls > /mesh/dummy.txt
RUN pip install --no-cache-dir --upgrade -e .

# Set working directory inside the container
WORKDIR /code

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED 1

# Copy only dependencies first to leverage Docker cache
COPY ./requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

