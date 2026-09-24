#!/usr/bin/env python3
"""
Light-Theme Ultra-High-Resolution PNG Chart Generator with Integrated Data Table.
Features:
- TrueType font rendering with system Ubuntu / DejaVu Sans fonts.
- Integrated data table grid directly aligned below the X-axis columns.
- Completely eliminates any floating badge overlaps or line obstructions.
- 2x Supersampling downsampled with Lanczos to 1200x720.
"""
import os
import json
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_ID = "mirage"
RAW_DIR = os.path.join(BASE_DIR, "results", "raw", SERVER_ID)
CHARTS_DIR = os.path.join(BASE_DIR, "results", "charts", SERVER_ID)
PROCESSED_DIR = os.path.join(BASE_DIR, "results", "processed", SERVER_ID)

os.makedirs(CHARTS_DIR, exist_ok=True)

def get_font(bold=False, size=16):
    font_candidates = [
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf" if bold else "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_light_png_chart(title, subtitle, x_label, y_label, series_data, x_ticks, output_file, unit=""):
    scale = 2
    w_2x = 1200 * scale
    h_2x = 720 * scale
    
    im_2x = Image.new("RGBA", (w_2x, h_2x), color=(255, 255, 255, 255))
    draw = ImageDraw.Draw(im_2x)

    margin_left = 110 * scale
    margin_right = 70 * scale
    margin_top = 125 * scale
    plot_h = 280 * scale

    plot_w = w_2x - margin_left - margin_right

    # Card border
    draw.rounded_rectangle([(8 * scale, 8 * scale), (w_2x - 8 * scale, h_2x - 8 * scale)], radius=14 * scale, fill=(255, 255, 255, 255), outline=(226, 232, 240, 255), width=2 * scale)

    # Fonts
    font_title = get_font(bold=True, size=21 * scale)
    font_sub = get_font(bold=False, size=12 * scale)
    font_axis = get_font(bold=True, size=11 * scale)
    font_tick = get_font(bold=False, size=11 * scale)
    font_tbl_hdr = get_font(bold=True, size=10 * scale)
    font_tbl_val = get_font(bold=True, size=11 * scale)
    font_leg_item = get_font(bold=True, size=11 * scale)

    # Title & Subtitle
    draw.text((margin_left, 24 * scale), title, font=font_title, fill=(15, 23, 42))
    draw.text((margin_left, 52 * scale), subtitle, font=font_sub, fill=(100, 116, 139))

    # Top Horizontal Legend
    leg_y = 76 * scale
    curr_leg_x = margin_left
    color_map = {
        "#059669": (5, 150, 105, 255),   # Emerald
        "#D97706": (217, 119, 6, 255),   # Amber
        "#4F46E5": (79, 70, 229, 255)    # Indigo
    }

    for idx, s in enumerate(series_data):
        c_rgba = color_map.get(s["color"], (79, 70, 229, 255))
        item_w = (len(s["name"]) * 7 + 36) * scale
        draw.rounded_rectangle([(curr_leg_x, leg_y), (curr_leg_x + item_w, leg_y + 24 * scale)], radius=12 * scale, fill=(248, 250, 252, 255), outline=(226, 232, 240, 255), width=1 * scale)
        draw.ellipse([(curr_leg_x + 8 * scale, leg_y + 7 * scale), (curr_leg_x + 18 * scale, leg_y + 17 * scale)], fill=c_rgba)
        draw.text((curr_leg_x + 23 * scale, leg_y + 4 * scale), s["name"], font=font_leg_item, fill=(51, 65, 85))
        curr_leg_x += item_w + 14 * scale

    all_vals = []
    for s in series_data:
        all_vals.extend(s["points"])
    max_y = max(all_vals) if all_vals else 100
    if max_y == 0: max_y = 1
    order = 10 ** int(len(str(int(max_y))) - 1) if max_y > 10 else 1
    max_y_rounded = ((int(max_y) // order) + 1) * order if order > 0 else 10
    if max_y_rounded < max_y * 1.15:
        max_y_rounded = int(max_y * 1.25) + 1

    y_ticks_count = 5
    y_tick_vals = [round(i * (max_y_rounded / y_ticks_count), 1) for i in range(y_ticks_count + 1)]

    def get_x(i, total):
        if total <= 1: return margin_left + plot_w / 2
        return margin_left + (i / (total - 1)) * plot_w

    def get_y(val):
        pct = val / float(max_y_rounded)
        return margin_top + plot_h - (pct * plot_h)

    # Grid Lines
    for yv in y_tick_vals:
        yp = get_y(yv)
        draw.line([(margin_left, yp), (margin_left + plot_w, yp)], fill=(241, 245, 249, 255), width=1 * scale)
        disp_val = int(yv) if yv == int(yv) else yv
        draw.text((margin_left - 65 * scale, yp - 7 * scale), f"{disp_val}{unit}", font=font_tick, fill=(100, 116, 139))

    # X-Axis Ticks & Labels on Chart
    total_x = len(x_ticks)
    for i, xt in enumerate(x_ticks):
        xp = get_x(i, total_x)
        draw.line([(xp, margin_top + plot_h), (xp, margin_top + plot_h + 8 * scale)], fill=(203, 213, 225, 255), width=2 * scale)
        draw.text((xp - 28 * scale, margin_top + plot_h + 14 * scale), xt, font=font_tick, fill=(71, 85, 105))

    # Y-Axis Title
    draw.text((16 * scale, margin_top + plot_h / 2 - 30 * scale), y_label.upper(), font=font_axis, fill=(100, 116, 139))

    # Precalculate all coordinates
    all_coords = []
    for idx, s in enumerate(series_data):
        coords = [(get_x(i, total_x), get_y(s["points"][i])) for i in range(total_x)]
        all_coords.append(coords)

    # Draw Lines & Circular Node Markers
    for idx, s in enumerate(series_data):
        c_rgba = color_map.get(s["color"], (79, 70, 229, 255))
        coords = all_coords[idx]
        for i in range(len(coords) - 1):
            draw.line([coords[i], coords[i+1]], fill=c_rgba, width=3 * scale)

        for i, (xp, yp) in enumerate(coords):
            draw.ellipse([(xp - 7 * scale, yp - 7 * scale), (xp + 7 * scale, yp + 7 * scale)], fill=(255, 255, 255, 255), outline=c_rgba, width=3 * scale)
            draw.ellipse([(xp - 3 * scale, yp - 3 * scale), (xp + 3 * scale, yp + 3 * scale)], fill=c_rgba)

    # =========================================================
    # INTEGRATED DATA TABLE (Zero Overlaps, 100% Legible)
    # =========================================================
    tbl_top = margin_top + plot_h + 52 * scale
    tbl_h = (len(series_data) * 34 + 36) * scale
    draw.rounded_rectangle([(margin_left, tbl_top), (margin_left + plot_w, tbl_top + tbl_h)], radius=10 * scale, fill=(248, 250, 252, 255), outline=(226, 232, 240, 255), width=1 * scale)

    # Table Header Row
    th_y = tbl_top + 10 * scale
    draw.text((margin_left + 14 * scale, th_y), "SERVICE / METRIC", font=font_tbl_hdr, fill=(100, 116, 139))
    for i, xt in enumerate(x_ticks):
        xp = get_x(i, total_x)
        draw.text((xp - 24 * scale, th_y), xt.upper(), font=font_tbl_hdr, fill=(100, 116, 139))

    draw.line([(margin_left, tbl_top + 26 * scale), (margin_left + plot_w, tbl_top + 26 * scale)], fill=(226, 232, 240, 255), width=1 * scale)

    # Table Data Rows
    for s_idx, s in enumerate(series_data):
        row_y = tbl_top + (34 + s_idx * 34) * scale
        c_rgba = color_map.get(s["color"], (79, 70, 229, 255))

        if s_idx > 0:
            draw.line([(margin_left, row_y - 8 * scale), (margin_left + plot_w, row_y - 8 * scale)], fill=(241, 245, 249, 255), width=1 * scale)

        # Service Label
        draw.ellipse([(margin_left + 14 * scale, row_y + 2 * scale), (margin_left + 22 * scale, row_y + 10 * scale)], fill=c_rgba)
        draw.text((margin_left + 28 * scale, row_y), s["name"], font=font_tbl_val, fill=(51, 65, 85))

        # Values aligned with column ticks
        for i in range(total_x):
            xp = get_x(i, total_x)
            val = s["points"][i]
            val_str = f"{val}{unit}"
            badge_w = (len(val_str) * 7.5 + 16) * scale
            badge_h = 20 * scale
            draw.rounded_rectangle([(xp - badge_w / 2, row_y - 3 * scale), (xp + badge_w / 2, row_y + badge_h - 3 * scale)], radius=4 * scale, fill=(255, 255, 255, 255), outline=(226, 232, 240, 255), width=1 * scale)
            draw.text((xp - (len(val_str) * 3.6 * scale), row_y), val_str, font=font_tbl_val, fill=(15, 23, 42))

    resample_filter = getattr(Image, 'LANCZOS', getattr(Image, 'ANTIALIAS', 1))
    im_final = im_2x.resize((1200, 720), resample=resample_filter)
    im_final.convert("RGB").save(output_file, "PNG")
    print(f"Generated clean light PNG chart with data table: {output_file}")

def generate_all_png_charts():
    with open(os.path.join(PROCESSED_DIR, "summary.json"), "r") as f:
        data = json.load(f)

    concurrencies = [1, 2, 4, 8]
    x_ticks = ["1 Client", "2 Clients", "4 Clients", "8 Clients"]
    colors = {"translation": "#059669", "asr": "#D97706", "tts": "#4F46E5"}
    labels = {"translation": "WiseAI Translation", "asr": "WiseAI ASR", "tts": "WiseAI TTS"}

    # 1. Throughput Chart
    tp_series = []
    for svc in ["translation", "asr", "tts"]:
        pts = [data[svc].get(str(c), data[svc].get(c, {})).get("throughput_rps", 0) for c in concurrencies]
        tp_series.append({"name": labels[svc], "color": colors[svc], "points": pts})
    draw_light_png_chart("WiseAI Microservices: Throughput Scaling", "Server: mirage | GPU: NVIDIA RTX 3090 (24GB) | Workload: Medium", "Client Concurrency", "Throughput (RPS)", tp_series, x_ticks, os.path.join(CHARTS_DIR, "throughput_vs_concurrency.png"), unit=" rps")

    # 2. Overall Latency Chart (Mean / Average Latency)
    lat_series = []
    for svc in ["translation", "asr", "tts"]:
        pts = [data[svc].get(str(c), data[svc].get(c, {})).get("latency_ms", {}).get("mean", 0) for c in concurrencies]
        lat_series.append({"name": labels[svc], "color": colors[svc], "points": pts})
    draw_light_png_chart("WiseAI Microservices: Overall Response Latency", "Server: mirage | GPU: NVIDIA RTX 3090 | Workload: Medium", "Client Concurrency", "Overall Latency (ms)", lat_series, x_ticks, os.path.join(CHARTS_DIR, "latency_vs_concurrency.png"), unit=" ms")

    # 3. GPU Util Chart
    gpu_series = []
    for svc in ["translation", "asr", "tts"]:
        pts = [data[svc].get(str(c), data[svc].get(c, {})).get("telemetry", {}).get("avg_gpu_util", 0) for c in concurrencies]
        gpu_series.append({"name": labels[svc], "color": colors[svc], "points": pts})
    draw_light_png_chart("WiseAI Microservices: Active GPU Utilization", "Server: mirage | GPU: NVIDIA RTX 3090 (390W Limit)", "Client Concurrency", "GPU Compute (%)", gpu_series, x_ticks, os.path.join(CHARTS_DIR, "gpu_utilization_vs_concurrency.png"), unit="%")

    # 5. RTF Chart
    rtf_series = []
    for svc in ["asr", "tts"]:
        pts = [data[svc].get(str(c), data[svc].get(c, {})).get("real_time_factor", {}).get("p50", 0) for c in concurrencies]
        rtf_series.append({"name": labels[svc], "color": colors[svc], "points": pts})
    draw_light_png_chart("Speech Services: Real-Time Factor (RTF)", "Real-Time Factor = Latency / Audio Duration (Lower is Faster)", "Client Concurrency", "Real-Time Factor", rtf_series, x_ticks, os.path.join(CHARTS_DIR, "real_time_factor.png"), unit="")

if __name__ == "__main__":
    generate_all_png_charts()
