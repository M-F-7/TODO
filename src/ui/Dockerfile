FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY src ./src

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "src/ui/mortalite.py", "--server.address=0.0.0.0", "--server.port=8501"]
