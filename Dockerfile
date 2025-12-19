# Use a slim Python image for the runtime
FROM python:3.13-slim

# Copy the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Change from the default of 'link', which is not supported by all file systems
ENV UV_LINK_MODE=copy

# Install dependencies before copying the application code to leverage Docker's cache
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

# Copy the application code
COPY ./app /app/app

# Place executable scripts in the environment's path
ENV PATH="/app/.venv/bin:$PATH"

# Expose the API port
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
