"""
visualisasi_ablation.py - Visualisasi Hasil Ablation Study (Tahap 2)
======================================================================
Membaca ablation_results.json dan menghasilkan:
  1. Bar chart perbandingan 4 skenario (Hit Rate, MRR, Context Precision)
  2. Radar chart profil performa tiap skenario
  3. Per-domain breakdown (Hit Rate per kategori)
  4. Latency comparison chart
  
Output: ablation_results.png (siap untuk laporan / presentasi skripsi)
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# ── Load data ──
BASE_DIR = os.path.dirname(__file__)
RESULTS_FILE = os.path.join(BASE_DIR, "ablation_results.json")
OUTPUT_PNG   = os.path.join(BASE_DIR, "ablation_results.png")

with open(RESULTS_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

scenarios   = list(data.keys())
hit_rates   = [data[s]["hit_rate_pct"]          for s in scenarios]
mrrs        = [data[s]["mrr"] * 100             for s in scenarios]   # scale to 0-100
precisions  = [data[s]["context_precision_pct"] for s in scenarios]
latencies   = [data[s]["avg_latency_s"] * 1000  for s in scenarios]   # ms

# ── Short labels ──
short_labels = [
    "Raw\n+ Dense",
    "Transformed\n+ Dense",
    "Raw\n+ Hybrid",
    "Transformed\n+ Hybrid",
]

# ── Color palette (premium dark-ish) ──
COLORS = ["#5B8AF5", "#F5A623", "#4CAF50", "#E91E8C"]
BG     = "#0F1117"
PANEL  = "#1A1D27"
TEXT   = "#E8EAF0"
GRID   = "#2A2D3A"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "text.color": TEXT,
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "axes.facecolor": PANEL,
    "figure.facecolor": BG,
    "axes.edgecolor": GRID,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linestyle": "--",
    "grid.alpha": 0.5,
})

fig = plt.figure(figsize=(18, 14))
fig.patch.set_facecolor(BG)

gs = GridSpec(3, 3, figure=fig, hspace=0.48, wspace=0.38)

x = np.arange(len(scenarios))
BAR_W = 0.6

# ────────────────────────────────────────────────
# PLOT 1: Hit Rate @ 5
# ────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
bars = ax1.bar(x, hit_rates, color=COLORS, width=BAR_W, zorder=3)
ax1.set_title("Hit Rate @ K=5 (%)", fontsize=13, fontweight="bold", pad=8)
ax1.set_ylim(0, 110)
ax1.set_xticks(x)
ax1.set_xticklabels(short_labels, fontsize=8.5)
ax1.set_ylabel("%", fontsize=10)
for bar, val in zip(bars, hit_rates):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
             f"{val:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold", color=TEXT)

# ────────────────────────────────────────────────
# PLOT 2: MRR (scaled x100)
# ────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
bars2 = ax2.bar(x, mrrs, color=COLORS, width=BAR_W, zorder=3)
ax2.set_title("Mean Reciprocal Rank (MRR × 100)", fontsize=13, fontweight="bold", pad=8)
ax2.set_ylim(0, 110)
ax2.set_xticks(x)
ax2.set_xticklabels(short_labels, fontsize=8.5)
ax2.set_ylabel("MRR × 100", fontsize=10)
for bar, val in zip(bars2, mrrs):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
             f"{val:.1f}", ha="center", va="bottom", fontsize=9, fontweight="bold", color=TEXT)

# ────────────────────────────────────────────────
# PLOT 3: Context Precision
# ────────────────────────────────────────────────
ax3 = fig.add_subplot(gs[0, 2])
bars3 = ax3.bar(x, precisions, color=COLORS, width=BAR_W, zorder=3)
ax3.set_title("Context Precision (%)", fontsize=13, fontweight="bold", pad=8)
ax3.set_ylim(0, 110)
ax3.set_xticks(x)
ax3.set_xticklabels(short_labels, fontsize=8.5)
ax3.set_ylabel("%", fontsize=10)
for bar, val in zip(bars3, precisions):
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
             f"{val:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold", color=TEXT)

# ────────────────────────────────────────────────
# PLOT 4: Radar Chart
# ────────────────────────────────────────────────
ax_radar = fig.add_subplot(gs[1, 0], polar=True)
metrics_radar  = ["Hit Rate", "MRR×100", "Ctx Precision"]
N = len(metrics_radar)
angles = [n / float(N) * 2 * np.pi for n in range(N)]
angles += angles[:1]

ax_radar.set_facecolor(PANEL)
ax_radar.set_theta_offset(np.pi / 2)
ax_radar.set_theta_direction(-1)
ax_radar.set_thetagrids(np.degrees(angles[:-1]), metrics_radar, fontsize=9)

for i, (sname, color) in enumerate(zip(scenarios, COLORS)):
    vals = [hit_rates[i], mrrs[i], precisions[i]]
    vals += vals[:1]
    ax_radar.plot(angles, vals, "o-", linewidth=2, color=color, label=short_labels[i].replace("\n", " "))
    ax_radar.fill(angles, vals, alpha=0.08, color=color)

ax_radar.set_ylim(0, 100)
ax_radar.set_title("Radar: Profil Performa\nPer Skenario", fontsize=11, fontweight="bold", pad=18, color=TEXT)
ax_radar.tick_params(colors=TEXT)
ax_radar.grid(color=GRID)

# ────────────────────────────────────────────────
# PLOT 5: Avg Latency (ms)
# ────────────────────────────────────────────────
ax5 = fig.add_subplot(gs[1, 1])
bars5 = ax5.bar(x, latencies, color=COLORS, width=BAR_W, zorder=3)
ax5.set_title("Avg Retrieval Latency (ms)", fontsize=13, fontweight="bold", pad=8)
ax5.set_xticks(x)
ax5.set_xticklabels(short_labels, fontsize=8.5)
ax5.set_ylabel("ms", fontsize=10)
for bar, val in zip(bars5, latencies):
    ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
             f"{val:.0f}ms", ha="center", va="bottom", fontsize=9, fontweight="bold", color=TEXT)

# ────────────────────────────────────────────────
# PLOT 6: Per-Domain Hit Rate Heatmap
# ────────────────────────────────────────────────
ax6 = fig.add_subplot(gs[1, 2])

all_domains = sorted(set(q["domain"] for s in scenarios for q in data[s]["per_query"]))
heatmap_data = []
for sname in scenarios:
    row = []
    per_q = data[sname]["per_query"]
    for dom in all_domains:
        dom_hits = [q["hit"] for q in per_q if q["domain"] == dom]
        row.append(sum(dom_hits) / len(dom_hits) * 100 if dom_hits else 0)
    heatmap_data.append(row)

hm = np.array(heatmap_data)
im = ax6.imshow(hm, aspect="auto", cmap="YlGn", vmin=0, vmax=100)
ax6.set_xticks(range(len(all_domains)))
ax6.set_xticklabels(all_domains, rotation=35, ha="right", fontsize=7.5)
ax6.set_yticks(range(len(scenarios)))
ax6.set_yticklabels(short_labels, fontsize=8)
ax6.set_title("Hit Rate per Domain (%)\n(Heatmap)", fontsize=11, fontweight="bold", pad=8)

for i in range(len(scenarios)):
    for j in range(len(all_domains)):
        val = hm[i, j]
        ax6.text(j, i, f"{val:.0f}", ha="center", va="center",
                 fontsize=8, color="black" if val > 50 else TEXT, fontweight="bold")

# ────────────────────────────────────────────────
# PLOT 7: Grouped bar — semua metrik sekaligus
# ────────────────────────────────────────────────
ax7 = fig.add_subplot(gs[2, :])

metric_names = ["Hit Rate @ K=5 (%)", "MRR × 100", "Context Precision (%)"]
metric_vals  = [hit_rates, mrrs, precisions]
n_metrics    = len(metric_names)
x7 = np.arange(n_metrics)
bar_width    = 0.18

for i, (sname, color, label) in enumerate(zip(scenarios, COLORS, short_labels)):
    offsets = x7 + (i - n_metrics/2 + 0.5) * bar_width
    vals = [metric_vals[m][i] for m in range(n_metrics)]
    b = ax7.bar(offsets, vals, width=bar_width, color=color, label=label.replace("\n", " "), zorder=3)
    for bar, v in zip(b, vals):
        ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
                 f"{v:.1f}", ha="center", va="bottom", fontsize=7.5, color=TEXT)

ax7.set_xticks(x7)
ax7.set_xticklabels(metric_names, fontsize=11)
ax7.set_ylim(0, 115)
ax7.set_title("Perbandingan Komprehensif Semua Skenario & Metrik", fontsize=13, fontweight="bold", pad=10)
ax7.set_ylabel("Nilai", fontsize=10)
ax7.legend(loc="upper right", fontsize=9, framealpha=0.3)

# ────────────────────────────────────────────────
# Judul utama & watermark
# ────────────────────────────────────────────────
fig.suptitle(
    "Ablation Study — RAG Hybrid Search Chatbot Universitas Gunadarma\n"
    "4 Skenario: {Raw|Transformed} Query × {Dense|Hybrid} Retrieval  •  N=30 pertanyaan uji",
    fontsize=14, fontweight="bold", color=TEXT, y=0.99
)

fig.text(0.99, 0.005, "Generated by ablation_study.py | Skripsi Chatbot RAG Gunadarma",
         ha="right", fontsize=7.5, color=GRID)

plt.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight", facecolor=BG)
print(f"[OK] Grafik disimpan: {OUTPUT_PNG}")
print(f"     Ukuran: {os.path.getsize(OUTPUT_PNG) / 1024:.1f} KB")
