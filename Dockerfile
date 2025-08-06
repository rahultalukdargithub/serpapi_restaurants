# Use the official Playwright base image (includes Python, Firefox, Chromium, WebKit)
FROM mcr.microsoft.com/playwright/python:v1.44.0

# Set working directory inside the container
WORKDIR /app

# Copy the Python script and other files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser binaries (Firefox, Chromium, WebKit)
RUN playwright install

# Command to run the scraper
CMD ["python", "final2.py"]
