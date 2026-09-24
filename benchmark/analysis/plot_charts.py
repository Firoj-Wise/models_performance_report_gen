#!/usr/bin/env python3
"""
Publication-Grade Light-Theme SVG Vector Chart Generator with Integrated Data Table.
Completely eliminates label overlap by using an integrated data table grid directly
aligned below the X-axis, while keeping the plot lines clean, elegant, and unobstructed.
"""
import os
import json
import glob

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def get_server_id():
    if os.environ.get("SERVER_ID"):
        return os.environ.get("SERVER_ID").strip()
    manifest_p = os.path.join(BASE_DIR, "config", "manifest.yaml")
    if os.path.exists(manifest_p):
        try:
            import yaml
            with open(manifest_p, "r") as f:
                m = yaml.safe_load(f)
                if m and "server" in m and "id" in m["server"]:
                    return str(m["server"]["id"]).strip()
        except Exception:
            pass
    import platform
    return platform.node().strip() or "localhost"

SERVER_ID = get_server_id()
RAW_DIR = os.path.join(BASE_DIR, "results", "raw", SERVER_ID)
CHARTS_DIR = os.path.join(BASE_DIR, "results", "charts", SERVER_ID)
PROCESSED_DIR = os.path.join(BASE_DIR, "results", "processed", SERVER_ID)

os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def generate_svg_line_chart(title, subtitle, x_label, y_label, series_data, x_ticks, output_file, unit=""):
    width = 960
    height = 570
    margin_left = 90
    margin_right = 50
    margin_top = 100
    plot_h = 240 # Height of plot area
    
    table_top = margin_top + plot_h + 40
    table_h = len(series_data) * 28 + 32

    plot_w = width - margin_left - margin_right

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

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif;">')
    
    # Gradients & Shadows
    svg.append('<defs>')
    svg.append('  <filter id="softShadow" x="-10%" y="-10%" width="120%" height="120%">')
    svg.append('    <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000000" flood-opacity="0.08"/>')
    svg.append('  </filter>')
    for idx, s in enumerate(series_data):
        c = s["color"]
        svg.append(f'  <linearGradient id="areaGrad_{idx}" x1="0" y1="0" x2="0" y2="1">')
        svg.append(f'    <stop offset="0%" stop-color="{c}" stop-opacity="0.18"/>')
        svg.append(f'    <stop offset="100%" stop-color="{c}" stop-opacity="0.01"/>')
        svg.append(f'  </linearGradient>')
    svg.append('</defs>')

    # Outer Card (Pure White with Crisp Border)
    svg.append(f'<rect width="{width}" height="{height}" fill="#ffffff" rx="14"/>')
    svg.append(f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" fill="none" stroke="#e2e8f0" stroke-width="1.5" rx="13"/>')

    # Title & Subtitle
    svg.append(f'<text x="{margin_left}" y="36" fill="#0f172a" font-size="19" font-weight="700" letter-spacing="-0.01em">{title}</text>')
    svg.append(f'<text x="{margin_left}" y="56" fill="#64748b" font-size="12.5">{subtitle}</text>')

    # Top Horizontal Legend
    leg_y = 74
    curr_leg_x = margin_left
    for idx, s in enumerate(series_data):
        item_w = len(s["name"]) * 7.5 + 32
        svg.append(f'<rect x="{curr_leg_x}" y="{leg_y}" width="{item_w}" height="22" rx="11" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1"/>')
        svg.append(f'<circle cx="{curr_leg_x + 11}" cy="{leg_y + 11}" r="4.5" fill="{s["color"]}"/>')
        svg.append(f'<text x="{curr_leg_x + 22}" y="{leg_y + 15}" fill="#334155" font-size="11" font-weight="600">{s["name"]}</text>')
        curr_leg_x += item_w + 12

    # Grid Lines & Y-Axis Labels
    for yv in y_tick_vals:
        yp = get_y(yv)
        svg.append(f'<line x1="{margin_left}" y1="{yp}" x2="{margin_left + plot_w}" y2="{yp}" stroke="#f1f5f9" stroke-width="1"/>')
        svg.append(f'<line x1="{margin_left}" y1="{yp}" x2="{margin_left + plot_w}" y2="{yp}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3"/>')
        disp_val = int(yv) if yv == int(yv) else yv
        svg.append(f'<text x="{margin_left - 12}" y="{yp + 4}" fill="#64748b" font-size="11.5" font-weight="500" text-anchor="end">{disp_val}{unit}</text>')

    # X-Axis Ticks & Labels on Chart
    total_x = len(x_ticks)
    for i, xt in enumerate(x_ticks):
        xp = get_x(i, total_x)
        svg.append(f'<line x1="{xp}" y1="{margin_top + plot_h}" x2="{xp}" y2="{margin_top + plot_h + 6}" stroke="#cbd5e1" stroke-width="1.5"/>')
        svg.append(f'<text x="{xp}" y="{margin_top + plot_h + 20}" fill="#475569" font-size="12" font-weight="600" text-anchor="middle">{xt}</text>')

    # Y-Axis Title
    svg.append(f'<text transform="rotate(-90)" x="-{margin_top + plot_h / 2}" y="24" fill="#64748b" font-size="11.5" font-weight="600" text-anchor="middle" letter-spacing="0.04em">{y_label.upper()}</text>')

    # Calculate Coordinates
    all_coords = []
    for idx, s in enumerate(series_data):
        coords = [(get_x(i, total_x), get_y(s["points"][i])) for i in range(total_x)]
        all_coords.append(coords)

    # Render Curves & Area Fills (Clean, no floating badges to block lines!)
    for idx, s in enumerate(series_data):
        c = s["color"]
        coords = all_coords[idx]
        
        area_d = [f"M {coords[0][0]},{coords[0][1]}"]
        line_d = [f"M {coords[0][0]},{coords[0][1]}"]
        for i in range(len(coords) - 1):
            p0 = coords[i]
            p1 = coords[i+1]
            cp1x = p0[0] + (p1[0] - p0[0]) / 2.0
            cp1y = p0[1]
            cp2x = p0[0] + (p1[0] - p0[0]) / 2.0
            cp2y = p1[1]
            curve_seg = f"C {cp1x},{cp1y} {cp2x},{cp2y} {p1[0]},{p1[1]}"
            area_d.append(curve_seg)
            line_d.append(curve_seg)
        area_d.append(f"L {coords[-1][0]},{margin_top + plot_h} L {coords[0][0]},{margin_top + plot_h} Z")
        
        svg.append(f'<path d="{" ".join(area_d)}" fill="url(#areaGrad_{idx})"/>')
        svg.append(f'<path d="{" ".join(line_d)}" fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round"/>')

        # Clean circular node markers
        for i, (xp, yp) in enumerate(coords):
            svg.append(f'<circle cx="{xp}" cy="{yp}" r="6" fill="#ffffff" stroke="{c}" stroke-width="2.5" filter="url(#softShadow)"/>')
            svg.append(f'<circle cx="{xp}" cy="{yp}" r="2.5" fill="{c}"/>')

    # =========================================================
    # INTEGRATED DATA TABLE (Zero Overlaps, 100% Readable)
    # =========================================================
    tbl_x = margin_left
    tbl_w = plot_w
    svg.append(f'<rect x="{tbl_x}" y="{table_top}" width="{tbl_w}" height="{table_h}" rx="8" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1"/>')

    # Table Header Row
    th_y = table_top + 20
    svg.append(f'<text x="{tbl_x + 14}" y="{th_y}" fill="#64748b" font-size="11" font-weight="700" letter-spacing="0.04em">SERVICE / METRIC</text>')
    for i, xt in enumerate(x_ticks):
        xp = get_x(i, total_x)
        svg.append(f'<text x="{xp}" y="{th_y}" fill="#64748b" font-size="11" font-weight="700" text-anchor="middle">{xt.upper()}</text>')

    svg.append(f'<line x1="{tbl_x}" y1="{table_top + 28}" x2="{tbl_x + tbl_w}" y2="{table_top + 28}" stroke="#e2e8f0" stroke-width="1"/>')

    # Table Data Rows
    for s_idx, s in enumerate(series_data):
        row_y = table_top + 50 + s_idx * 28
        c = s["color"]
        
        # Row zebra line
        if s_idx > 0:
            svg.append(f'<line x1="{tbl_x}" y1="{row_y - 18}" x2="{tbl_x + tbl_w}" y2="{row_y - 18}" stroke="#f1f5f9" stroke-width="1"/>')

        # Service Label with colored indicator
        svg.append(f'<circle cx="{tbl_x + 18}" cy="{row_y - 4}" r="4" fill="{c}"/>')
        svg.append(f'<text x="{tbl_x + 28}" y="{row_y}" fill="#334155" font-size="11.5" font-weight="600">{s["name"]}</text>')

        # Value cells exactly aligned with column ticks
        for i in range(total_x):
            xp = get_x(i, total_x)
            val = s["points"][i]
            val_str = f"{val}{unit}"
            # Light pill behind value
            badge_w = len(val_str) * 7.5 + 14
            svg.append(f'<rect x="{xp - badge_w / 2}" y="{row_y - 14}" width="{badge_w}" height="18" rx="4" fill="#ffffff" stroke="#e2e8f0" stroke-width="1"/>')
            svg.append(f'<text x="{xp}" y="{row_y - 1}" fill="#0f172a" font-size="11" font-weight="700" text-anchor="middle">{val_str}</text>')

    svg.append('</svg>')

    with open(output_file, "w") as f:
        f.write("\n".join(svg))
    print(f"Generated clean light SVG chart with data table: {output_file}")

def generate_all_charts():
    with open(os.path.join(PROCESSED_DIR, "summary.json"), "r") as f:
        data = json.load(f)

    concurrencies = [1, 2, 4, 8]
    x_ticks = ["1 Client", "2 Clients", "4 Clients", "8 Clients"]
    colors = {"translation": "#059669", "asr": "#D97706", "tts": "#4F46E5"}
    labels = {"translation": "WiseAI Translation", "asr": "WiseAI ASR", "tts": "WiseAI TTS"}

    # 1. Throughput Chart (RPS)
    tp_series = []
    for svc in ["translation", "asr", "tts"]:
        pts = [data[svc].get(str(c), data[svc].get(c, {})).get("throughput_rps", 0) for c in concurrencies]
        tp_series.append({"name": labels[svc], "color": colors[svc], "points": pts})
    generate_svg_line_chart("WiseAI Microservices: Throughput Scaling", f"Server: {SERVER_ID} | GPU: NVIDIA RTX 3090 (24GB) | Workload: Medium", "Client Concurrency", "Throughput (RPS)", tp_series, x_ticks, os.path.join(CHARTS_DIR, "throughput_vs_concurrency.svg"), unit=" rps")

    # 2. Overall Latency Chart (Mean / Average Latency)
    lat_series = []
    for svc in ["translation", "asr", "tts"]:
        pts = [data[svc].get(str(c), data[svc].get(c, {})).get("latency_ms", {}).get("mean", 0) for c in concurrencies]
        lat_series.append({"name": labels[svc], "color": colors[svc], "points": pts})
    generate_svg_line_chart("WiseAI Microservices: Overall Response Latency", f"Server: {SERVER_ID} | GPU: NVIDIA RTX 3090 | Workload: Medium", "Client Concurrency", "Overall Latency (ms)", lat_series, x_ticks, os.path.join(CHARTS_DIR, "latency_vs_concurrency.svg"), unit=" ms")

    # 3. GPU Util Chart
    gpu_series = []
    for svc in ["translation", "asr", "tts"]:
        pts = [data[svc].get(str(c), data[svc].get(c, {})).get("telemetry", {}).get("avg_gpu_util", 0) for c in concurrencies]
        gpu_series.append({"name": labels[svc], "color": colors[svc], "points": pts})
    generate_svg_line_chart("WiseAI Microservices: Active GPU Utilization", f"Server: {SERVER_ID} | GPU: NVIDIA RTX 3090 (390W Limit)", "Client Concurrency", "GPU Compute Utilization (%)", gpu_series, x_ticks, os.path.join(CHARTS_DIR, "gpu_utilization_vs_concurrency.svg"), unit="%")

    # 5. RTF Chart
    rtf_series = []
    for svc in ["asr", "tts"]:
        pts = [data[svc].get(str(c), data[svc].get(c, {})).get("real_time_factor", {}).get("p50", 0) for c in concurrencies]
        rtf_series.append({"name": labels[svc], "color": colors[svc], "points": pts})
    generate_svg_line_chart("Speech Services: Real-Time Factor (RTF)", "Real-Time Factor = Latency / Audio Duration (Lower is Faster)", "Client Concurrency", "Real-Time Factor", rtf_series, x_ticks, os.path.join(CHARTS_DIR, "real_time_factor.svg"), unit="")

if __name__ == "__main__":
    generate_all_charts()
