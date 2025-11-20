# Use python base image
FROM python:3.13-slim-bullseye

COPY requirements.txt .
#update pip & install dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Set the timezone to Africa/Nairobi
RUN ln -sf /usr/share/zoneinfo/Africa/Nairobi /etc/localtime

COPY . .

# Use the startup script as entrypoint to run both services
ENTRYPOINT ["python", "main.py"]