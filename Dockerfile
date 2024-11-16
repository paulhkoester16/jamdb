# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN apt update -y
RUN apt-get install -y graphviz

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements/requirements.txt,target=requirements/requirements.txt \
    --mount=type=bind,source=requirements/requirements_dev.txt,target=requirements/requirements_dev.txt \
    python -m pip install -r requirements/requirements_dev.txt

RUN --mount=type=bind,source=jamdb,target=jamdb \
    --mount=type=bind,source=setup.py,target=setup.py \
    python -m pip install ./


RUN --mount=type=bind,source=tests,target=tests \
    --mount=type=bind,source=data,target=data \
    pytest --cov jamdb \
        --cov-branch \
        --junitxml=test-report.xml \
        --cov-report html:coverage_reports/htmlcov \
        --cov-report xml:coverage_reports/coverage.xml \
        --cov-report term \
        tests

# Switch to the non-privileged user to run the application.
USER appuser

# Copy the source code into the container.
COPY jamdb jamdb
COPY app app


# port needs to match that defined in compose.yaml
CMD flask --app app:init_app run --host=0.0.0.0 --port=8989




