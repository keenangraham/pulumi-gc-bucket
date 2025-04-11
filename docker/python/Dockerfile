FROM python:3.12.1-bullseye

ENV PYTHONDONTWRITEBYTECODE 1

ENV PYTHONUNBUFFERED 1

ENV VIRTUAL_ENV=/opt/venv

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m igvf

RUN python -m venv $VIRTUAL_ENV

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN chown -R igvf:igvf $VIRTUAL_ENV

WORKDIR /igvf

COPY --chown=igvfd:igvfd requirements.txt .

RUN pip install -r requirements.txt

COPY --chown=igvf:igvf . .

RUN chmod +x *.sh

USER igvf

ENTRYPOINT ["./entrypoint.sh"]

CMD ["./run.sh"]