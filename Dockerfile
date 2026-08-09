# Menggunakan OS Linux kecil yang sudah ada Python-nya
FROM python:3.10-slim

# Menginstal Inkscape dan Ghostscript
RUN apt-get update && apt-get install -y \
    inkscape \
    ghostscript \
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
