FROM python:3.13-alpine

# Only runtime packages needed
RUN apk add --no-cache tzdata ca-certificates \
    && cp /usr/share/zoneinfo/Africa/Nairobi /etc/localtime \
    && echo "Africa/Nairobi" > /etc/timezone \
    && pip install --upgrade pip

COPY . .
RUN pip install -r requirements.txt

ENV TZ=Africa/Nairobi

ENTRYPOINT ["python", "main.py"]