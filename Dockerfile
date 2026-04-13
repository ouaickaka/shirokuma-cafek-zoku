FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download unidic dictionary for MeCab (needed by add-furigana.py)
RUN python3 -c "import unidic; print('unidic ok')" 2>/dev/null || true

CMD ["bash"]
