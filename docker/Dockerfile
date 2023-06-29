####################################
#### Basic Python Environment ####
####################################
FROM ubuntu:22.04

# set args for build only
ARG DEBIAN_FRONTEND=noninteractive
ARG http_proxy=http://www.bessy.de:3128
ARG https_proxy=http://www.bessy.de:3128


RUN apt-get update \
  && apt-get -y --no-install-recommends install \
        build-essential \
        ca-certificates \
        curl \
        less \
	cmake \
	g++ \
	gfortan \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*


# docker build -f cython3.Dockerfile -t cython3:latest .
# sudo singularity build cython3_from_docker.sif docker-daemon://cython3:latest

RUN groupadd -g 999 appuser && \
    useradd -r -u 999 -g appuser appuser

RUN mkdir /workdir ; \
    chown appuser:appuser /workdir ; \
    mkdir /home/appuser ; \
    chown appuser:appuser /home/appuser


WORKDIR /workdir


USER root

CMD ["/bin/bash"]
