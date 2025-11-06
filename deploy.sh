#!/bin/bash

docker build -f Dockerfile -t tipspesa-ai .

docker tag tipspesa-ai:latest dennismuga/tipspesa-ai:latest

docker push dennismuga/tipspesa-ai:latest 