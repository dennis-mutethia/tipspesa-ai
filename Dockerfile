#Use small python alpine base
FROM python:3.13-alpine

# Set Local Timezone
RUN apk add --no-cache tzdata ca-certificates && \
    cp /usr/share/zoneinfo/Africa/Nairobi /etc/localtime && \
    echo "Africa/Nairobi" > /etc/timezone 

#set local timezone
ENV TZ=Africa/Nairobi

#install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

#copy rest of the code
COPY . .

#Run application
ENTRYPOINT ["python", "main.py"]