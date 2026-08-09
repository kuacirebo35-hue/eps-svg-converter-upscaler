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

            # ==========================================
            # FITUR BARU: SVG ke SVG (Hanya Upscale)
            # ==========================================
            if mode == "SVG ke SVG (Upscale)":
                if not filename.lower().endswith('.svg'):
                    log_messages.append(f"❌ Gagal: {filename} (Bukan file SVG!)")
                    continue
                
                # Menambahkan embel-embel "_4x" di nama file agar jelas
                out_filename = os.path.splitext(filename)[0] + f"_{scale_factor}x.svg"
                out_path = os.path.join(os.path.dirname(in_path), out_filename)
                
                shutil.copy2(in_path, out_path)
                
                if scale_factor > 1:
                    scale_svg_math(out_path, scale_factor)
                
                zipf.write(out_path, arcname=out_filename)
                log_messages.append(f"✅ Sukses: {out_filename}")
                os.remove(out_path)
                continue # Lanjut ke file berikutnya (Lewati proses Inkscape)

            # ==========================================
            # FITUR LAMA: Konversi menggunakan Inkscape
            # ==========================================
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
                    log_messages.append(f"✅ Sukses: {out_filename}")
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

# --- CSS KUSTOM UNTUK TAMPILAN DESKTOP & PEMBATASAN SCROLL ---
custom_css = """
body, .gradio-container { background-color: #121212 !important; }

.sidebar { 
    background-color: #1a1a1a !important; 
    padding: 25px 20px !important; 
    border-right: 1px solid #333 !important; 
    border-radius: 10px;
    height: 100%;
}

.gold-title h2 { color: #D4AF37 !important; font-weight: 900 !important; text-align: center; margin-bottom: 5px; letter-spacing: 1px;}
.version-badge { color: #888; text-align: center; font-size: 13px; font-weight: bold; margin-bottom: 30px; display: block; }

.submit-btn { 
    background: linear-gradient(90deg, #D4AF37 0%, #B5952F 100%) !important; 
    border: none !important; 
    color: #121212 !important; 
    font-weight: 800 !important; 
    font-size: 16px !important; 
    height: 50px !important;
    margin-top: 20px !important;
    box-shadow: 0 4px 10px rgba(212, 175, 55, 0.2) !important;
}
.submit-btn:hover { transform: scale(1.02) !important; }

.file-preview { max-height: 250px !important; overflow-y: auto !important; }

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #1E1E1E; }
::-webkit-scrollbar-thumb { background: #D4AF37; border-radius: 4px; }

.wa-link { color: #25D366; text-decoration: none; font-weight: bold; font-size: 13px; display: block; text-align: center; margin-top: 20px;}
.wa-link:hover { color: #1DA851; text-decoration: underline; }
"""

theme = gr.themes.Default(primary_hue="amber").set(
    body_background_fill="#121212",
    body_background_fill_dark="#121212",
    block_background_fill="#1E1E1E",
    block_background_fill_dark="#1E1E1E",
    block_border_color="#333333",
    block_border_color_dark="#333333",
    background_fill_primary="#1E1E1E",
    background_fill_primary_dark="#1E1E1E"
)

with gr.Blocks(theme=theme, css=custom_css, js="""function() { document.body.classList.add('dark'); }""") as app:
    
    with gr.Row():
        with gr.Column(scale=1, min_width=260, elem_classes="sidebar"):
            # Update Judul dan Versi
            gr.Markdown("## EPS TO SVG\n## CONVERTER", elem_classes="gold-title")
            gr.HTML('<span class="version-badge">V 1.2.0</span>')
            
            gr.Markdown("**MODE KONVERSI**")
            # Menambah opsi baru di dropdown
            mode_input = gr.Dropdown(choices=["EPS ke SVG", "SVG ke EPS", "SVG ke SVG (Upscale)"], value="EPS ke SVG", show_label=False)
            
            gr.Markdown("**UPSCALE VEKTOR & ARTBOARD**")
            upscale_input = gr.Dropdown(choices=["1x (Original)", "2x", "4x", "5x", "6x", "7x", "8x"], value="4x", show_label=False)
            
            btn_convert = gr.Button("⚡ MULAI KONVERSI", elem_classes=["submit-btn"])
            
            gr.HTML('''
                <div style="margin-top: 50px; text-align: center; border-top: 1px solid #333; padding-top: 15px;">
                    <p style="font-size: 12px; color: #888; margin-bottom: 5px;">Developer by <b>Muhammad Fairuz</b></p>
                    <a href="https://chat.whatsapp.com/JsXK1fNRSFKE1bQfYlGimt" target="_blank" class="wa-link">
                        🔗 Gabung Group WA FORUM STOCK AI
                    </a>
                </div>
            ''')

        with gr.Column(scale=3):
            gr.Markdown("### Daftar Antrean Batch", elem_classes="gold-title")
            
            file_input = gr.File(label="Tarik & Lepas File Di Sini (Drop Area)", file_count="multiple", height=300)
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Monitor Proses")
                    log_output = gr.Textbox(show_label=False, lines=6, interactive=False, placeholder="Siap memproses. Silakan tambahkan file input.")
                
                with gr.Column(scale=1):
                    gr.Markdown("### Hasil Konversi")
                    file_output = gr.File(label="Download File ZIP Di Sini", file_count="single")

    btn_convert.click(
        fn=convert_files, 
        inputs=[file_input, mode_input, upscale_input], 
        outputs=[file_output, log_output]
    )

if __name__ == "__main__":
    app.queue(default_concurrency_limit=1).launch(server_name="0.0.0.0", server_port=10000)
