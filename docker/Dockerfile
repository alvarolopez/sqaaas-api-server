FROM python
MAINTAINER Pablo Orviz <orviz@ifca.unican.es>

RUN mkdir /sqaaas-api-server
COPY . /sqaaas-api-server
WORKDIR /sqaaas-api-server
RUN pip3 install .

COPY ./docker/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
