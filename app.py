import gradio as gr
import subprocess
import xml.etree.ElementTree as ET
import os
import shutil
import re

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
        return []
    
    scale_factor = 1
    if upscale_str != "1x (Original)":
        scale_factor = int(upscale_str.replace("x", ""))

    hasil_konversi = []

    for file_obj in files:
        in_path = file_obj.name
        filename = os.path.basename(in_path)
        
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
            "inkscape", 
            target_in_path, 
            "--export-type=svg" if mode == "EPS ke SVG" else "--export-type=eps", 
            f"--export-filename={out_path}"
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if temp_svg and os.path.exists(temp_svg):
                os.remove(temp_svg)

            if os.path.exists(out_path):
                if mode == "EPS ke SVG" and scale_factor > 1:
                    scale_svg_math(out_path, scale_factor)
                hasil_konversi.append(out_path)
                
        except Exception as e:
            print(f"Gagal: {e}")

    return hasil_konversi

with gr.Blocks(theme=gr.themes.Monochrome()) as app:
    gr.Markdown("# ⚡ EPS TO SVG CONVERTER BATCH")
    gr.Markdown("Web App Gratis. Upload banyak file sekaligus, server akan mengantre dan memprosesnya satu per satu.")

    with gr.Row():
        with gr.Column():
            mode_input = gr.Radio(["EPS ke SVG", "SVG ke EPS"], label="Mode Konversi", value="EPS ke SVG")
            upscale_input = gr.Dropdown(["1x (Original)", "2x", "4x", "5x", "6x", "7x", "8x"], label="Upscale Vektor", value="4x")
            file_input = gr.File(label="Upload File Disini (Bisa blok banyak file)", file_count="multiple")
            btn_convert = gr.Button("🚀 MULAI KONVERSI", variant="primary")

        with gr.Column():
            file_output = gr.File(label="Hasil File Siap Download", file_count="multiple")
            gr.Markdown("**Catatan:** File akan otomatis terhapus dari server saat Anda menutup halaman web ini.")

    btn_convert.click(
        fn=convert_files, 
        inputs=[file_input, mode_input, upscale_input], 
        outputs=[file_output]
    )

if __name__ == "__main__":
    # PENTING: Pengaturan khusus agar bisa berjalan di Render.com
    app.queue(default_concurrency_limit=1).launch(server_name="0.0.0.0", server_port=10000)
