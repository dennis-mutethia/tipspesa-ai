#!/bin/bash

#remove eks image if exists
docker rmi -f tipspesa-ai

#build the image
docker build -t tipspesa-ai .

#remove container if running
docker rm -f tipspesa-ai  

#run the container
docker run -d --name tipspesa-ai tipspesa-ai
