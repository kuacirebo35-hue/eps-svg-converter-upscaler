# Menggunakan OS Linux kecil yang sudah ada Python-nya
FROM python:3.10-slim

# Menginstal Inkscape, Ghostscript, dan Modul Python untuk Inkscape
RUN apt-get update && apt-get install -y \
    inkscape \
    ghostscript \
    python3-tinycss2 \
    python3-cssselect \
    python3-lxml \
    && rm -rf /var/lib/apt/lists/*

# Menyiapkan folder kerja di dalam server
WORKDIR /app

# Mengopi file requirements dan menginstal Gradio
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Mengopi semua kode Anda (app.py) ke dalam server
COPY . .

# Membuka jalur komunikasi untuk Render
EXPOSE 10000

# Menjalankan aplikasinya!
CMD ["python", "app.py"]
