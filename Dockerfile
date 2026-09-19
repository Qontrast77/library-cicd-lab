# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Layer caching optimization #1: requirements.txt is copied and installed
# BEFORE the rest of the source code. Docker only re-runs this layer (and
# everything after it) when requirements.txt actually changes - editing
# app.py alone reuses the cached dependency-install layer.
COPY requirements.txt .

# Layer caching optimization #2: BuildKit cache mount for pip's own
# download/build cache. Unlike a normal image layer, this cache persists
# across builds even when requirements.txt DOES change (e.g. one new
# dependency added) - pip does not need to re-download packages it already
# fetched in a previous build. Requires BuildKit (DOCKER_BUILDKIT=1).
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt gunicorn

COPY . .

EXPOSE 5000
ENV PORT=5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
