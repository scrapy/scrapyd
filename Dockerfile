FROM alpine:3.5

RUN apk add --no-cache --update --virtual .build-deps  \
        ca-certificates \
        libffi-dev \
        libxml2-dev \
        libxslt-dev \
        openssl-dev && \
    apk add --no-cache \
        build-base \
        libxslt \
        libffi \
        libxslt \
        openssl \
        python \
        py-pip \
        python-dev && \
    pip install --upgrade scrapyd && \
    apk del .build-deps
WORKDIR /app
COPY docker/scrapyd.conf /app/scrapyd.conf
EXPOSE 6800
ENTRYPOINT ["scrapyd"]

