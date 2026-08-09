import gradio as gr
import subprocess
import xml.etree.ElementTree as ET
import os
import shutil
import re
import zipfile

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

def convert_files(files, mode, upscale_str):
    if not files:
        return None, "Tidak ada file yang dipilih."
    
    scale_factor = 1
    if upscale_str != "1x (Original)":
        scale_factor = int(upscale_str.replace("x", ""))

    log_messages = []
    zip_filename = "Hasil_Konversi_Batch.zip"
    zip_path = os.path.join(os.getcwd(), zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_obj in files:
            in_path = file_obj if isinstance(file_obj, str) else file_obj.name
            filename = os.path.basename(in_path)
            log_messages.append(f"⏳ Memproses: {filename}...")

            out_ext = ".svg" if mode == "EPS ke SVG" else ".eps"
            out_filename = os.path.splitext(filename)[0] + out_ext
            out_path = os.path.join(os.path.dirname(in_path), out_filename)
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
                    log_messages.append(f"✅ Sukses: {out_filename} (Masuk ZIP)")
                    os.remove(out_path)
                else:
                    error_msg = result.stderr.strip()
                    if not error_msg:
                        error_msg = "Format tidak terbaca server."
                    log_messages.append(f"❌ Gagal: {filename}\n   (Error: {error_msg})")
            except Exception as e:
                log_messages.append(f"❌ Error Sistem: {str(e)}")

    log_messages.append("📦 Semua proses selesai! File ZIP siap diunduh.")
    return zip_path, "\n".join(log_messages)

custom_css = """
.gradio-container { max-width: 1100px !important; margin: auto; }
.submit-btn { background: linear-gradient(90deg, #D4AF37 0%, #B5952F 100%) !important; border: none !important; color: #121212 !important; font-weight: 800 !important; font-size: 16px !important; transition: all 0.3s ease-in-out !important; box-shadow: 0 4px 10px rgba(212, 175, 55, 0.3) !important; }
.submit-btn:hover { transform: scale(1.02) !important; box-shadow: 0 6px 15px rgba(212, 175, 55, 0.5) !important; }
.footer-box { text-align: center; margin-top: 40px; padding: 25px; border-top: 1px solid #ddd; border-radius: 10px; background-color: transparent; }
.wa-btn { display: inline-block; padding: 12px 24px; background-color: #25D366; color: white !important; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 15px; transition: 0.3s; box-shadow: 0 4px 6px rgba(37, 211, 102, 0.3); margin-top: 12px; }
.wa-btn:hover { background-color: #1DA851; transform: translateY(-2px); box-shadow: 0 6px 12px rgba(37, 211, 102, 0.4); }
"""

with gr.Blocks(theme=gr.themes.Soft(primary_hue="amber"), css=custom_css) as app:
    gr.HTML('''
        <div style="text-align: center; margin-bottom: 30px; padding-top: 20px;">
            <h1 style="color: #D4AF37; margin-bottom: 5px; font-weight: 900; font-size: 32px;">
                ⚡ EPS TO SVG CONVERTER V1.1.0
            </h1>
            <p style="color: #888; font-size: 15px;">
                Batch Converter Berbasis Cloud - Cepat, Gratis, & Stabil (Auto ZIP)
            </p>
        </div>
    ''')

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Panel Pengaturan")
            with gr.Group():
                mode_input = gr.Radio(["EPS ke SVG", "SVG ke EPS"], label="Mode Konversi", value="EPS ke SVG")
                upscale_input = gr.Dropdown(["1x (Original)", "2x", "4x", "5x", "6x", "7x", "8x"], label="Upscale Vektor", value="4x")
            
            gr.Markdown("### 📂 Upload File Mentah")
            file_input = gr.File(label="Tarik & Lepas File (Bisa blok banyak file)", file_count="multiple")
            btn_convert = gr.Button("🚀 MULAI KONVERSI SEKARANG", elem_classes=["submit-btn"])

        with gr.Column(scale=2):
            gr.Markdown("### 📥 Hasil Unduhan (Otomatis jadi 1 ZIP)")
            file_output = gr.File(label="Download File ZIP Di Sini", file_count="single")
            
            gr.Markdown("### 🖥️ Monitor Proses")
            log_output = gr.Textbox(label="Cek status antrean dan error di sini", lines=10, interactive=False)
    
    gr.HTML('''
        <div class="footer-box">
            <p style="font-size: 14px; margin-bottom: 0px; color: #555;">
                Developed by <span style="font-weight: bold; color: #333;">Muhammad Fairuz</span>
            </p>
            <p style="font-size: 13px; color: #888; margin-top: 2px;">
                © 2026 Hak Cipta Dilindungi
            </p>
            <a href="https://chat.whatsapp.com/JsXK1fNRSFKE1bQfYlGimt" target="_blank" class="wa-btn">
                <i class="fa fa-whatsapp"></i> 💬 Gabung Group WA FORUM STOCK AI
            </a>
        </div>
    ''')

    btn_convert.click(
        fn=convert_files, 
        inputs=[file_input, mode_input, upscale_input], 
        outputs=[file_output, log_output]
    )

if __name__ == "__main__":
    app.queue(default_concurrency_limit=1).launch(server_name="0.0.0.0", server_port=10000)
