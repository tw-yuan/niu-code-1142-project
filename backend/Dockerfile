FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml 2>/dev/null || \
    uv pip install --system --no-cache fastapi uvicorn[standard] sqlalchemy aiosqlite greenlet \
    python-multipart PyMuPDF python-docx tiktoken openai chromadb \
    "python-jose[cryptography]" "passlib[bcrypt]" python-dotenv httpx pydantic-settings

COPY app ./app

RUN mkdir -p data/uploads data/chromadb

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
