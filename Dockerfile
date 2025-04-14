FROM python:3.13-alpine3.21

ARG APP_VERSION

LABEL org.opencontainers.image.source=https://github.com/bognarbalazs/gatekeeper-metrics-reporter
LABEL org.opencontainers.image.description="Gatekeeper-metrics-reporter"
LABEL org.opencontainers.image.licenses=MIT
LABEL app.version=${APP_VERSION}

# Set the working directory
WORKDIR /app

RUN apk add git && adduser -S nonroot && pip install git+https://github.com/bognarbalazs/gatekeeper-metrics-reporter.git@${APP_VERSION} && apk del git && rm -rf /var/cache/apk/* && echo "" > /etc/apk/repositories

USER nonroot

ENTRYPOINT [ "gatekeeper-metrics-reporter" ]