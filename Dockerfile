FROM ghcr.io/astral-sh/uv:latest

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app

EXPOSE 5000

WORKDIR /app/app
CMD ["uv", "run", "app.py"]
