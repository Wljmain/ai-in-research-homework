FROM python:3.11-slim

# Basic tools that an agent may need when setting up additional
# analysis software inside the container.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Scientific Python stack available to the agent.
RUN pip install --no-cache-dir \
    numpy==2.1.3 \
    scipy==1.14.1

# Benchmark data. Nothing from authoring/ is copied into the
# agent's environment.
COPY data /root/data

WORKDIR /root

CMD ["/bin/bash"]