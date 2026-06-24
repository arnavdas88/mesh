# Use official slim Python image for small size
FROM python:3.11-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install mesh
WORKDIR /mesh
COPY ./ /mesh
RUN pip install --no-cache-dir --upgrade .

# Set working directory inside the container
WORKDIR /code

# Copy only dependencies first to leverage Docker cache
COPY ./requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

