FROM alpine:latest

RUN apk update \
    && apk add python3 build-base python3-dev linux-headers \
    && python3 -m ensurepip \
    && python3 -m pip install --upgrade pip

RUN pip3 install speedtest-cli 'influxdb-client[ciso]' ischedule psutil

RUN addgroup -S speedtest && adduser -S speedtest -G speedtest

RUN mkdir /speedtest
WORKDIR /speedtest

COPY speedtest-logger.py /speedtest/

USER speedtest

ENTRYPOINT ["python3", "/speedtest/speedtest-logger.py"]