FROM ubuntu:latest

#RUN apk add --no-cache curl
RUN apt-get update && apt-get install -y curl

RUN mkdir /darwin && cd /darwin && \
    curl -SL -O http://biorecipes.com/darwin/darwin.linux64 && \
    curl -SL http://biorecipes.com/darwin/darwin-lib.tgz | tar -xz  && \
    chmod +x darwin.linux64

RUN echo "#!/bin/bash\nulimit -s unlimited\n/darwin/darwin.linux64 -l /darwin/lib $*\n" > /darwin/darwin && \
    chmod +x /darwin/darwin 

#ENTRYPOINT ["/darwin/darwin"]
