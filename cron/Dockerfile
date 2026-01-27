FROM debian:trixie-slim

RUN apt-get update \
    && DEBIAN_FRONTEND=nointeractive apt-get install --no-install-recommends -y \
        cron \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --chmod=644 cronjob /etc/cron.d/cronjob

ENTRYPOINT ["cron", "-f"]
