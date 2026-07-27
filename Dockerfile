# Use the official Python image from the Docker Hub
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Set the working directory
    WORKDIR=/app

# Install system dependencies including LibreOffice for document conversion
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libreoffice \
        libreoffice-core \
        fonts-dejavu-core \
        fonts-liberation \
        libheif-dev \
        libfreetype6-dev \
        libjpeg-dev \
        libopenjp2-7-dev \
        libpng-dev \
        libtiff-dev \
        zlib1g-dev \
        # Clean up apt cache to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app
COPY --chown=appuser:appuser . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Environment variable for port (default to 8000 if not set)
ENV PORT=8000

# Run the application with gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} app:app"]
# Trigger rebuild
