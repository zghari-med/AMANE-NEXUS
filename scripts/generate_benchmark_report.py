"""
Genere benchmark-report.html -- resultats PFE AMANE-NEXUS
Usage : python scripts/generate_benchmark_report.py [benchmark_results.json]
"""
import json, sys, os
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_FILE = sys.argv[1] if len(sys.argv) > 1 else "backend/data/benchmark_results.json"

with open(DATA_FILE, encoding="utf-8") as f:
    d = json.load(f)

meta   = d["_meta"]
env    = d["environment"]
yolo   = d["yolo_inference_benchmarks"]
acc    = d["model_accuracy"]
behav  = d["by_behavior"]
sys_b  = d["system_benchmarks"]
calib  = d["calibration_history"]
ds     = d["datasets_tested"]
proc   = d.get("processing_benchmarks", {})

def pbar(val, max_val=100, color="#3b82f6", height=10):
    pct = min(val / max_val * 100, 100)
    return (f'<div style="background:#e2e8f0;border-radius:4px;height:{height}px;overflow:hidden;margin-top:4px">'
            f'<div style="width:{pct:.1f}%;height:100%;background:{color};border-radius:4px"></div></div>')

def metric_cell(label, val, unit="", color="#1e293b"):
    return f'<div class="metric"><div class="metric-val" style="color:{color}">{val}<span class="metric-unit">{unit}</span></div><div class="metric-lbl">{label}</div></div>'

# ── Comportements ─────────────────────────────────────────────────────────────
bev_rows = ""
COLORS = {"fall":"#ef4444","crowding":"#f97316","abandoned_object":"#3b82f6"}
for key, b in behav.items():
    v   = b["validation"]
    col = COLORS.get(key, "#6b7280")
    f1  = v["f1_score"]
    pr  = v["precision_pct"]
    re  = v["recall_pct"]
    bev_rows += f"""
    <tr>
      <td><span class="dot" style="background:{col}"></span><strong>{b['label']}</strong></td>
      <td>{v['primary_dataset']}</td>
      <td>{v.get('images_tested') or v.get('videos_tested','—')}</td>
      <td>{pr:.1f}%{pbar(pr,100,col,6)}</td>
      <td>{re:.1f}%{pbar(re,100,col,6)}</td>
      <td><strong>{f1:.3f}</strong>{pbar(f1*100,100,col,6)}</td>
      <td>{v.get('mean_iou','—') if isinstance(v.get('mean_iou'),str) else f"{v['mean_iou']:.3f}"}</td>
      <td style="font-size:.8rem;color:#64748b">{b.get('best_metric','')[:60]}</td>
    </tr>"""

# ── Datasets comparatifs ──────────────────────────────────────────────────────
def ds_rows(items, color):
    out = ""
    for it in items:
        sel = it.get("selected", False)
        bg  = "#f0fdf4" if sel else ""
        icon = "✔ Retenu" if sel else "Rejeté"
        badge_style = ("background:#dcfce7;color:#15803d" if sel
                       else "background:#f1f5f9;color:#64748b")
        out += f"""<tr style="background:{bg}">
          <td>{it['name']}</td>
          <td>{it.get('images') or it.get('videos_tested','—')}</td>
          <td><strong>{it['f1']:.3f}</strong>{pbar(it['f1']*100,100,color,6)}</td>
          <td>{f"{it['iou']:.3f}" if 'iou' in it else '—'}</td>
          <td><span class="badge" style="{badge_style}">{icon}</span></td>
        </tr>"""
    return out

# ── API timings ───────────────────────────────────────────────────────────────
api_rows = ""
api_max = max(sys_b["api_response_time_ms"].values())
for ep, ms in sys_b["api_response_time_ms"].items():
    api_rows += f"""<tr>
      <td><code>/api/{ep.replace('_','/')}</code></td>
      <td>{ms} ms{pbar(ms, api_max, "#3b82f6", 6)}</td>
      <td>{"🟢 Excellent" if ms < 30 else "🟡 Bon" if ms < 100 else "🔴 Lent"}</td>
    </tr>"""

# ── Calibration ───────────────────────────────────────────────────────────────
calib_rows = "".join(
    f'<tr><td>{c["date"]}</td><td><code>{c["change"]}</code></td><td style="color:#64748b">{c["reason"]}</td></tr>'
    for c in calib
)

# ── Processing benchmarks ─────────────────────────────────────────────────────
proc_rows = ""
for name, p in proc.items():
    ratio = p.get("speedup_ratio", 0)
    color_ratio = "#16a34a" if ratio >= 1 else "#d97706"
    proc_rows += f"""<tr>
      <td><code>{name}</code></td>
      <td>{p['duration_s']}s</td>
      <td>{p['total_frames']}</td>
      <td>{p['processed_frames']} ({p['processed_frames']/p['total_frames']*100:.0f}%)</td>
      <td>{p['processing_time_s']}s</td>
      <td style="color:{color_ratio}"><strong>{ratio:.2f}x</strong></td>
      <td>{p['events_detected']}</td>
    </tr>"""

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rapport de Performance — AMANE-NEXUS PFE</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Segoe UI',Arial,sans-serif; background:#f8fafc; color:#1e293b; }}
  header {{ background:linear-gradient(135deg,#1e3a5f 0%,#1d4ed8 100%); color:#fff; padding:36px 48px; }}
  header h1 {{ font-size:1.9rem; font-weight:700; }}
  header p  {{ margin-top:6px; color:#bfdbfe; font-size:.95rem; }}
  .container {{ max-width:1100px; margin:32px auto; padding:0 24px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:28px; }}
  .kpi {{ background:#fff; border-radius:12px; padding:20px 24px; box-shadow:0 1px 4px rgba(0,0,0,.08); text-align:center; }}
  .kpi .val {{ font-size:2rem; font-weight:800; }}
  .kpi .lbl {{ font-size:.78rem; color:#64748b; margin-top:4px; text-transform:uppercase; letter-spacing:.05em; }}
  .card {{ background:#fff; border-radius:12px; box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:28px; overflow:hidden; }}
  .card-header {{ background:#eff6ff; padding:14px 24px; font-weight:700; font-size:1rem; border-bottom:1px solid #dbeafe; display:flex; align-items:center; gap:10px; }}
  .env-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:0; }}
  .env-item {{ padding:14px 20px; border-bottom:1px solid #f1f5f9; border-right:1px solid #f1f5f9; }}
  .env-item:nth-child(3n) {{ border-right:none; }}
  .env-key {{ font-size:.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.06em; margin-bottom:3px; }}
  .env-val {{ font-weight:600; font-size:.92rem; }}
  table {{ width:100%; border-collapse:collapse; font-size:.88rem; }}
  th {{ background:#f8fafc; padding:11px 14px; text-align:left; font-weight:600; color:#475569; border-bottom:2px solid #e2e8f0; font-size:.8rem; text-transform:uppercase; letter-spacing:.04em; }}
  td {{ padding:11px 14px; border-bottom:1px solid #f1f5f9; vertical-align:middle; }}
  tr:last-child td {{ border-bottom:none; }}
  tr:hover td {{ background:#f8fafc; }}
  .dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:7px; }}
  .badge {{ border-radius:20px; padding:3px 10px; font-size:.78rem; font-weight:700; }}
  .metric {{ display:inline-flex; flex-direction:column; align-items:center; padding:16px 20px; }}
  .metric-val {{ font-size:1.7rem; font-weight:800; }}
  .metric-unit {{ font-size:1rem; font-weight:400; margin-left:2px; color:#64748b; }}
  .metric-lbl {{ font-size:.75rem; color:#64748b; margin-top:4px; text-align:center; }}
  .metrics-row {{ display:flex; flex-wrap:wrap; gap:0; border-bottom:1px solid #f1f5f9; }}
  .metrics-row .metric {{ border-right:1px solid #f1f5f9; }}
  .metrics-row .metric:last-child {{ border-right:none; }}
  code {{ background:#f1f5f9; padding:2px 6px; border-radius:4px; font-size:.84rem; }}
  .section-title {{ font-size:.8rem; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:.08em; padding:12px 20px; background:#fafafa; border-bottom:1px solid #f1f5f9; }}
  footer {{ text-align:center; color:#94a3b8; font-size:.8rem; padding:32px; }}
</style>
</head>
<body>
<header>
  <h1>Rapport de Performance</h1>
  <p>AMANE-NEXUS v{meta['version']} &nbsp;·&nbsp; {meta['description']} &nbsp;·&nbsp; Généré le {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</p>
</header>

<div class="container">

  <!-- KPIs globaux -->
  <div class="kpi-grid">
    <div class="kpi">
      <div class="val" style="color:#1d4ed8">{acc['global']['f1_score']:.3f}</div>
      <div class="lbl">F1-Score global</div>
    </div>
    <div class="kpi">
      <div class="val" style="color:#16a34a">{acc['global']['precision_pct']:.1f}%</div>
      <div class="lbl">Précision globale</div>
    </div>
    <div class="kpi">
      <div class="val" style="color:#d97706">{yolo['avg_fps']}</div>
      <div class="lbl">FPS moyen (CPU)</div>
    </div>
    <div class="kpi">
      <div class="val" style="color:#7c3aed">{meta['total_images_tested'] + meta['total_videos_tested']}</div>
      <div class="lbl">Images + vidéos testées</div>
    </div>
  </div>

  <!-- Environnement -->
  <div class="card">
    <div class="card-header">🖥 Environnement d'exécution</div>
    <div class="env-grid">
      <div class="env-item"><div class="env-key">Système</div><div class="env-val">{env['os']}</div></div>
      <div class="env-item"><div class="env-key">CPU</div><div class="env-val">{env['cpu']}</div></div>
      <div class="env-item"><div class="env-key">RAM</div><div class="env-val">{env['ram_gb']} Go</div></div>
      <div class="env-item"><div class="env-key">GPU</div><div class="env-val">{env['gpu']}</div></div>
      <div class="env-item"><div class="env-key">Modèle YOLO</div><div class="env-val">{env['yolo_model']} · {env['model_size_mb']} Mo</div></div>
      <div class="env-item"><div class="env-key">Résolution</div><div class="env-val">{env['input_resolution']} · CPU only</div></div>
    </div>
  </div>

  <!-- Inférence YOLOv8 -->
  <div class="card">
    <div class="card-header">⚡ Benchmarks d'inférence YOLOv8n (100 frames · 640×640 · CPU)</div>
    <div class="metrics-row">
      {metric_cell("Temps moy.", f"{yolo['avg_inference_ms']:.1f}", " ms", "#1d4ed8")}
      {metric_cell("Temps min.", f"{yolo['min_inference_ms']:.1f}", " ms", "#16a34a")}
      {metric_cell("Temps max.", f"{yolo['max_inference_ms']:.1f}", " ms", "#dc2626")}
      {metric_cell("Écart-type", f"{yolo['std_inference_ms']:.1f}", " ms", "#6b7280")}
      {metric_cell("P95", f"{yolo['percentile_95_ms']:.1f}", " ms", "#d97706")}
      {metric_cell("FPS brut", f"{yolo['avg_fps']}", "", "#7c3aed")}
      {metric_cell("FPS effectif (SKIP=3)", f"{yolo['effective_fps_with_skip3']:.1f}", "", "#16a34a")}
    </div>
    <div style="padding:14px 20px;font-size:.85rem;color:#64748b;border-top:1px solid #f1f5f9">
      💡 {yolo['note']}
    </div>
  </div>

  <!-- Précision par comportement -->
  <div class="card">
    <div class="card-header">🎯 Précision par comportement détecté</div>
    <table>
      <thead>
        <tr>
          <th>Comportement</th><th>Dataset principal</th><th>Échantillons</th>
          <th>Précision</th><th>Rappel</th><th>F1-Score</th><th>IoU moyen</th><th>Point fort</th>
        </tr>
      </thead>
      <tbody>{bev_rows}</tbody>
    </table>
  </div>

  <!-- Benchmarks vidéo -->
  <div class="card">
    <div class="card-header">🎬 Benchmarks de traitement vidéo complet</div>
    <table>
      <thead><tr><th>Vidéo</th><th>Durée</th><th>Frames totales</th><th>Frames traitées</th><th>Temps traitement</th><th>Ratio temps réel</th><th>Événements</th></tr></thead>
      <tbody>{proc_rows}</tbody>
    </table>
    <div style="padding:12px 20px;font-size:.82rem;color:#64748b">
      * Ratio &lt; 1 = plus lent que temps réel (attendu en mode CPU sans GPU)
    </div>
  </div>

  <!-- Comparaison datasets -->
  <div class="card">
    <div class="card-header">📂 Comparaison des datasets — sélection finale</div>
    <div class="section-title">🔴 Chute (Fall Detection)</div>
    <table>
      <thead><tr><th>Dataset</th><th>Échantillons</th><th>F1-Score</th><th>IoU</th><th>Décision</th></tr></thead>
      <tbody>{ds_rows(ds['fall_datasets'], "#ef4444")}</tbody>
    </table>
    <div class="section-title">🟠 Attroupement (Crowd Detection)</div>
    <table>
      <thead><tr><th>Dataset</th><th>Échantillons</th><th>F1-Score</th><th>IoU</th><th>Décision</th></tr></thead>
      <tbody>{ds_rows(ds['crowd_datasets'], "#f97316")}</tbody>
    </table>
    <div class="section-title">🔵 Objet abandonné</div>
    <table>
      <thead><tr><th>Dataset</th><th>Échantillons</th><th>F1-Score</th><th>IoU</th><th>Décision</th></tr></thead>
      <tbody>{ds_rows(ds['abandoned_datasets'], "#3b82f6")}</tbody>
    </table>
  </div>

  <!-- API Response times -->
  <div class="card">
    <div class="card-header">🌐 Temps de réponse API Flask</div>
    <table>
      <thead><tr><th>Endpoint</th><th>Temps de réponse</th><th>Évaluation</th></tr></thead>
      <tbody>{api_rows}</tbody>
    </table>
  </div>

  <!-- Calibration history -->
  <div class="card">
    <div class="card-header">🔧 Historique de calibration des seuils</div>
    <table>
      <thead><tr><th>Date</th><th>Modification</th><th>Raison</th></tr></thead>
      <tbody>{calib_rows}</tbody>
    </table>
  </div>

</div>

</body>
</html>"""

out = "benchmark-report.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"[OK] {out} genere -- F1={acc['global']['f1_score']:.3f} -- FPS={yolo['avg_fps']} -- {meta['total_images_tested']}img + {meta['total_videos_tested']}vid")
