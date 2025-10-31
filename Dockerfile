# Use python base image
FROM python:3.13-slim-bullseye

# Update packages and clean up
RUN apt-get update \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
#update pip & install dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Set the timezone to Africa/Nairobi
RUN ln -sf /usr/share/zoneinfo/Africa/Nairobi /etc/localtime

EXPOSE 8080

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
