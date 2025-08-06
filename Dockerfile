# ✅ Base image with Playwright (includes Python, Node.js, and Firefox)
FROM mcr.microsoft.com/playwright/python:v1.44.0

# Set the working directory
WORKDIR /app

# Copy all files to the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Firefox, Chromium, WebKit)
RUN playwright install

# Expose port for FastAPI (Render will map this)
EXPOSE 8000

# Start FastAPI server using Uvicorn (serves main.py)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
