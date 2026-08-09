import gradio as gr
import subprocess
import xml.etree.ElementTree as ET
import os
import shutil
import re
import zipfile
import time

# Fungsi bantuan untuk menghitung ukuran file (KB/MB)
def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def scale_svg_math(svg_path, scale):
    try:
        ET.register_namespace('', "http://www.w3.org/2000/svg")
        ET.register_namespace('xlink', "http://www.w3.org/1999/xlink")
        ET.register_namespace('sodipodi', "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd")
        ET.register_namespace('inkscape', "http://www.inkscape.org/namespaces/inkscape")
        tree = ET.parse(svg_path)
        root = tree.getroot()
        if 'viewBox' in root.attrib:
            vb = list(map(float, root.attrib['viewBox'].replace(',', ' ').split()))
            root.attrib['viewBox'] = f"{vb[0]*scale} {vb[1]*scale} {vb[2]*scale} {vb[3]*scale}"
        for attr in ['width', 'height']:
            if attr in root.attrib:
                val = root.attrib[attr]
                match = re.match(r"([0-9.]+)([a-zA-Z%]*)", val)
                if match:
                    num = float(match.group(1))
                    unit = match.group(2)
                    root.attrib[attr] = f"{num * scale}{unit}"
        for child in root:
            tag_name = child.tag.split('}')[-1]
            if tag_name in ['defs', 'metadata', 'namedview', 'title', 'desc']:
                continue
            current_transform = child.get('transform', '')
            if current_transform:
                child.set('transform', f'scale({scale}) {current_transform}')
            else:
                child.set('transform', f'scale({scale})')
        tree.write(svg_path, encoding='utf-8', xml_declaration=True)
        return True
    except Exception as e:
        print(f"Error scaling SVG: {e}")
        return False

# MENGGUNAKAN GENERATOR (YIELD) AGAR TABEL UPDATE SECARA LIVE
def convert_files(files, mode, upscale_str):
    if not files:
        yield None, [["-", "Tidak ada file yang dipilih", "-", "Error"]]
        return
    
    scale_factor = 1
    if upscale_str != "1x (Original)":
        scale_factor = int(upscale_str.replace("x", ""))

    MAX_RETRIES = 3 # Batas maksimal percobaan jika gagal

    # 1. Menyiapkan Data Tabel Awal
    table_data = []
    for i, file_obj in enumerate(files):
        in_path = file_obj if isinstance(file_obj, str) else file_obj.name
        fname = os.path.basename(in_path)
        fsize = format_size(os.path.getsize(in_path))
        table_data.append([i + 1, fname, fsize, "⏳ Menunggu..."])
    
    yield None, table_data

    zip_filename = "Hasil_Konversi_Batch.zip"
    zip_path = os.path.join(os.getcwd(), zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for i, file_obj in enumerate(files):
            in_path = file_obj if isinstance(file_obj, str) else file_obj.name
            filename = os.path.basename(in_path)
            
            # ==========================================
            # MODE 1: SVG ke SVG (Hanya Upscale)
            # ==========================================
            if mode == "SVG ke SVG (Upscale)":
                table_data[i][3] = "🔄 Memproses..."
                yield None, table_data

                if not filename.lower().endswith('.svg'):
                    table_data[i][3] = "❌ Gagal (Bukan SVG)"
                    yield None, table_data
                    continue
                
                out_filename = os.path.splitext(filename)[0] + f"_{scale_factor}x.svg"
                out_path = os.path.join(os.path.dirname(in_path), out_filename)
                
                try:
                    shutil.copy2(in_path, out_path)
                    if scale_factor > 1:
                        scale_svg_math(out_path, scale_factor)
                    zipf.write(out_path, arcname=out_filename)
                    table_data[i][3] = "✅ Sukses"
                    os.remove(out_path)
                except Exception:
                    table_data[i][3] = "❌ Gagal Eksekusi"
                
                yield None, table_data
                continue

            # ==========================================
            # MODE 2: EPS ke EPS (Hanya Upscale)
            # ==========================================
            if mode == "EPS ke EPS (Upscale)":
                if not filename.lower().endswith('.eps'):
                    table_data[i][3] = "❌ Gagal (Bukan EPS)"
                    yield None, table_data
                    continue
                
                out_filename = os.path.splitext(filename)[0] + f"_{scale_factor}x.eps"
                out_path = os.path.join(os.path.dirname(in_path), out_filename)
                
                if scale_factor == 1:
                    shutil.copy2(in_path, out_path)
                    zipf.write(out_path, arcname=out_filename)
                    table_data[i][3] = "✅ Sukses"
                    os.remove(out_path)
                    yield None, table_data
                    continue
                
                # SISTEM RETRY 3X UNTUK EPS KE EPS
                for attempt in range(1, MAX_RETRIES + 1):
                    table_data[i][3] = f"🔄 Memproses (Coba {attempt}/3)..."
                    yield None, table_data
                    
                    temp_svg = in_path + ".temp.svg"
                    cmd1 = ["inkscape", in_path, "--export-type=svg", f"--export-filename={temp_svg}"]
                    
                    try:
                        subprocess.run(cmd1, capture_output=True, text=True, check=True)
                        scale_svg_math(temp_svg, scale_factor)
                        cmd2 = ["inkscape", temp_svg, "--export-type=eps", f"--export-filename={out_path}"]
                        subprocess.run(cmd2, capture_output=True, text=True, check=True)
                        
                        zipf.write(out_path, arcname=out_filename)
                        table_data[i][3] = "✅ Sukses"
                        os.remove(out_path)
                        if os.path.exists(temp_svg): os.remove(temp_svg)
                        break # SUKSES! Keluar dari loop retry
                    except Exception as e:
                        if os.path.exists(temp_svg): os.remove(temp_svg)
                        if attempt == MAX_RETRIES:
                            table_data[i][3] = "❌ Gagal Server"
                        else:
                            time.sleep(1) # Jeda 1 detik sebelum coba lagi
                            
                yield None, table_data
                continue

            # ==========================================
            # MODE 3 & 4: EPS ke SVG atau SVG ke EPS
            # ==========================================
            out_ext = ".svg" if mode == "EPS ke SVG" else ".eps"
            out_filename = os.path.splitext(filename)[0] + out_ext
            out_path = os.path.join(os.path.dirname(in_path), out_filename)
            
            # SISTEM RETRY 3X
            for attempt in range(1, MAX_RETRIES + 1):
                table_data[i][3] = f"🔄 Memproses (Coba {attempt}/3)..."
                yield None, table_data
                
                target_in_path = in_path
                temp_svg = None

                if mode == "SVG ke EPS" and scale_factor > 1:
                    temp_svg = in_path + ".temp.svg"
                    shutil.copy2(in_path, temp_svg)
                    scale_svg_math(temp_svg, scale_factor)
                    target_in_path = temp_svg 

                cmd = [
                    "inkscape", target_in_path, 
                    "--export-type=svg" if mode == "EPS ke SVG" else "--export-type=eps", 
                    f"--export-filename={out_path}"
                ]

                try:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if temp_svg and os.path.exists(temp_svg):
                        os.remove(temp_svg)
                    
                    if os.path.exists(out_path):
                        if mode == "EPS ke SVG" and scale_factor > 1:
                            scale_svg_math(out_path, scale_factor)
                        
                        zipf.write(out_path, arcname=out_filename)
                        table_data[i][3] = "✅ Sukses"
                        os.remove(out_path)
                        break # SUKSES! Keluar dari loop retry
                    else:
                        if attempt == MAX_RETRIES:
                            error_msg = result.stderr.strip()
                            if not error_msg: error_msg = "Format corrupt."
                            table_data[i][3] = f"❌ Gagal ({error_msg[:15]}...)"
                        else:
                            time.sleep(1) # Jeda 1 detik sebelum coba lagi
                except Exception as e:
                    if attempt == MAX_RETRIES:
                        table_data[i][3] = "❌ Error Sistem"
                    else:
                        time.sleep(1)

            yield None, table_data

    # Proses selesai
    yield zip_path, table_data


# ==========================================
# TAMPILAN UI
# ==========================================
custom_css = """
.gradio-container { max-width: 1050px !important; margin: auto; padding: 20px; }
.file-upload-box { max-height: 250px !important; overflow-y: auto !important; }
.wa-link { display: inline-block; padding: 10px 20px; background-color: #25D366; color: white !important; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; margin-top: 10px; transition: 0.2s; }
.wa-link:hover { background-color: #1DA851; transform: translateY(-2px); }
.table-wrap { max-height: 350px !important; overflow-y: auto !important; width: 100% !important; }
.zip-download-box { height: 85px !important; min-height: 85px !important; overflow: hidden !important; }
.zip-download-box > div { min-height: 85px !important; height: 85px !important; }

/* Desain tombol stop merah */
.btn-stop { background: #ef4444 !important; border: none !important; color: white !important; }
.btn-stop:hover { background: #dc2626 !important; transform: scale(1.02); }
"""

theme = gr.themes.Soft(primary_hue="blue", neutral_hue="slate")

with gr.Blocks(theme=theme, css=custom_css) as app:
    
    gr.HTML('''
        <div style="text-align: center; margin-bottom: 25px; padding-bottom: 10px; border-bottom: 1px solid #eaeaea;">
            <h1 style="color: #1e293b; font-weight: 800; font-size: 28px; margin-bottom: 5px;">
                ⚡ EPS TO SVG CONVERTER
            </h1>
            <span style="background-color: #e2e8f0; color: #475569; padding: 3px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">
                V 1.5.0
            </span>
            <p style="color: #64748b; font-size: 14px; margin-top: 10px;">
                Batch Converter Berbasis Cloud - Cepat, Gratis, & Otomatis ZIP
            </p>
        </div>
    ''')

    with gr.Row():
        with gr.Column(scale=1, min_width=300):
            gr.Markdown("### ⚙️ Pengaturan Input")
            with gr.Row():
                mode_input = gr.Dropdown(
                    choices=["EPS ke SVG", "SVG ke EPS", "SVG ke SVG (Upscale)", "EPS ke EPS (Upscale)"], 
                    value="EPS ke SVG", 
                    label="Mode Konversi"
                )
                upscale_input = gr.Dropdown(
                    choices=["1x (Original)", "2x", "4x", "5x", "6x", "7x", "8x"], 
                    value="4x", 
                    label="Upscale Vektor"
                )
                
        with gr.Column(scale=1, min_width=300):
            gr.Markdown("### 📥 Hasil Monitor")
            file_output = gr.File(label="Download File ZIP Di Sini", file_count="single", elem_classes="zip-download-box")

    gr.Markdown("### 📂 Tarik & Lepas File Di Sini")
    file_input = gr.File(label="Upload Banyak File Sekaligus", file_count="multiple", elem_classes="file-upload-box")
    
    btn_convert = gr.Button("🚀 MULAI KONVERSI SEKARANG", variant="primary", size="lg")

    gr.Markdown("### 🖥️ Status Antrean (Live Tabel)")
    log_output = gr.Dataframe(
        headers=["No", "Nama File", "Size", "Keterangan"],
        datatype=["number", "str", "str", "str"],
        label="Daftar Proses",
        interactive=False,
        wrap=True,
        elem_classes="table-wrap"
    )

    # TOMBOL BARU: STOP / CANCEL PROSES DITARUH DI BAWAH TABEL
    btn_stop = gr.Button("🛑 BATALKAN PROSES", elem_classes="btn-stop", size="lg")

    gr.HTML('''
        <div style="text-align: center; margin-top: 50px; border-top: 1px solid #eaeaea; padding-top: 20px;">
            <p style="font-size: 13px; color: #64748b; margin-bottom: 5px;">
                Developed by <b>Muhammad Fairuz</b> © 2026
            </p>
            <a href="https://chat.whatsapp.com/JsXK1fNRSFKE1bQfYlGimt" target="_blank" class="wa-link">
                💬 Gabung Group WA FORUM STOCK AI
            </a>
        </div>
    ''')

    # MENGAITKAN FUNGSI KLIK
    # 1. Menjalankan proses konversi
    konversi_event = btn_convert.click(
        fn=convert_files, 
        inputs=[file_input, mode_input, upscale_input], 
        outputs=[file_output, log_output]
    )
    
    # 2. Mengaitkan tombol Batal agar menyela proses di atas
    btn_stop.click(fn=None, inputs=None, outputs=None, cancels=[konversi_event])

if __name__ == "__main__":
    app.queue(default_concurrency_limit=1).launch(server_name="0.0.0.0", server_port=10000)
