#!/bin/bash

#remove eks image if exists
#docker rmi -f tipspesa-ai

#build the image
docker build -t tipspesa-ai .  

#stop container
docker rm -f tipspesa-ai  

#run container
docker run -d --name tipspesa-ai tipspesa-ai

##optional tag and push to dockerhub
docker tag tipspesa-ai:latest dennismuga/tipspesa-ai:latest

#push
docker push dennismuga/tipspesa-ai:latest
