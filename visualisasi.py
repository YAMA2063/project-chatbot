"""
Visualisasi Hasil Pengujian Akurasi & Performa Chatbot RAG
Data dihitung langsung dari 30 skenario pengujian (bukan angka manual).
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ============================================================
# DATA MENTAH — 30 skenario pengujian
# (No, Akurat?, Halusinasi?, Waktu respons dalam detik)
# ============================================================
raw_data = [
    (1, "Y", "T", 4.75), (2, "Y", "T", 4.09), (3, "Y", "T", 3.48),
    (4, "Y", "T", 5.86), (5, "Y", "T", 4.27), (6, "Y", "T", 5.65),
    (7, "Y", "T", 4.80), (8, "T", "T", 4.59), (9, "Y", "T", 5.82),
    (10, "Y", "T", 4.36), (11, "Y", "T", 5.17), (12, "Y", "T", 6.46),
    (13, "T", "Y", 5.00), (14, "Y", "T", 7.16), (15, "Y", "T", 5.95),
    (16, "Y", "T", 7.16), (17, "T", "Y", 6.94), (18, "Y", "T", 6.65),
    (19, "T", "Y", 6.13), (20, "Y", "T", 3.66), (21, "Y", "T", 8.00),
    (22, "Y", "T", 3.78), (23, "Y", "T", 6.02), (24, "Y", "T", 3.77),
    (25, "Y", "T", 4.46), (26, "Y", "T", 1.98), (27, "Y", "T", 2.34),
    (28, "Y", "T", 2.15), (29, "Y", "T", 3.11), (30, "Y", "T", 0.88),
]

total = len(raw_data)
akurat_count = sum(1 for r in raw_data if r[1] == "Y")
bebas_halusinasi_count = sum(1 for r in raw_data if r[2] == "T")
waktu_respons = [r[3] for r in raw_data]

akurasi_pct = akurat_count / total * 100
bebas_halusinasi_pct = bebas_halusinasi_count / total * 100
rata_waktu = np.mean(waktu_respons)

print(f"Akurasi: {akurat_count}/{total} = {akurasi_pct:.2f}%")
print(f"Bebas Halusinasi: {bebas_halusinasi_count}/{total} = {bebas_halusinasi_pct:.2f}%")
print(f"Rata-rata waktu respons: {rata_waktu:.2f} detik")

# ============================================================
# STYLE — palet warna elegan, konsisten, profesional
# ============================================================
COLOR_PRIMARY = "#6C3FC5"      # ungu (senada tema Gunadarma)
COLOR_PRIMARY_LIGHT = "#E8DFFB"
COLOR_SECONDARY = "#2FA88A"    # teal
COLOR_SECONDARY_LIGHT = "#DBF2EC"
COLOR_TEXT = "#2B2B2B"
COLOR_GRID = "#E5E5E5"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "text.color": COLOR_TEXT,
    "axes.edgecolor": COLOR_GRID,
    "axes.labelcolor": COLOR_TEXT,
    "xtick.color": COLOR_TEXT,
    "ytick.color": COLOR_TEXT,
})

fig = plt.figure(figsize=(13, 5), dpi=200)
gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.4], wspace=0.35)

# ---------- DONUT 1: AKURASI ----------
ax1 = fig.add_subplot(gs[0])
sizes = [akurasi_pct, 100 - akurasi_pct]
ax1.pie(
    sizes,
    colors=[COLOR_PRIMARY, COLOR_PRIMARY_LIGHT],
    startangle=90,
    counterclock=False,
    wedgeprops=dict(width=0.32, edgecolor="white", linewidth=3),
    radius=1.0,
)
ax1.set_xlim(-1.35, 1.35)
ax1.set_ylim(-1.35, 1.35)
ax1.text(0, 0.10, f"{akurasi_pct:.2f}%", ha="center", va="center",
          fontsize=19, fontweight="bold", color=COLOR_PRIMARY)
ax1.text(0, -0.18, f"{akurat_count} dari {total} skenario", ha="center", va="center",
          fontsize=9, color="#777777")
ax1.set_title("Akurasi Jawaban", fontsize=13, fontweight="bold", pad=18, color=COLOR_TEXT)

# ---------- DONUT 2: BEBAS HALUSINASI ----------
ax2 = fig.add_subplot(gs[1])
sizes2 = [bebas_halusinasi_pct, 100 - bebas_halusinasi_pct]
ax2.pie(
    sizes2,
    colors=[COLOR_SECONDARY, COLOR_SECONDARY_LIGHT],
    startangle=90,
    counterclock=False,
    wedgeprops=dict(width=0.32, edgecolor="white", linewidth=3),
    radius=1.0,
)
ax2.set_xlim(-1.35, 1.35)
ax2.set_ylim(-1.35, 1.35)
ax2.text(0, 0.10, f"{bebas_halusinasi_pct:.2f}%", ha="center", va="center",
          fontsize=19, fontweight="bold", color=COLOR_SECONDARY)
ax2.text(0, -0.18, f"{bebas_halusinasi_count} dari {total} skenario", ha="center", va="center",
          fontsize=9, color="#777777")
ax2.set_title("Bebas Halusinasi", fontsize=13, fontweight="bold", pad=18, color=COLOR_TEXT)

# ---------- SEBARAN WAKTU RESPONS ----------
ax3 = fig.add_subplot(gs[2])
no_list = [r[0] for r in raw_data]
bar_colors = [COLOR_PRIMARY if r[1] == "Y" else "#D14343" for r in raw_data]
bars = ax3.bar(no_list, waktu_respons, color=bar_colors, width=0.65, zorder=3)

ax3.axhline(rata_waktu, color="#444444", linestyle="--", linewidth=1.3, zorder=2)
ax3.text(total + 0.6, rata_waktu, f"Rata-rata\n{rata_waktu:.2f} dtk",
          va="center", ha="left", fontsize=9.5, color="#444444", fontweight="bold")

ax3.set_xlim(0, total + 5)
ax3.set_ylim(0, max(waktu_respons) + 1.5)
ax3.set_xlabel("Nomor Skenario Pengujian", fontsize=10)
ax3.set_ylabel("Waktu Respons (detik)", fontsize=10)
ax3.set_title("Sebaran Waktu Respons per Skenario", fontsize=13, fontweight="bold", pad=18, color=COLOR_TEXT)
ax3.grid(axis="y", color=COLOR_GRID, linewidth=0.8, zorder=0)
ax3.spines["top"].set_visible(False)
ax3.spines["right"].set_visible(False)
ax3.spines["left"].set_visible(False)
ax3.tick_params(left=False)

legend_elems = [
    mpatches.Patch(color=COLOR_PRIMARY, label="Jawaban Akurat"),
    mpatches.Patch(color="#D14343", label="Jawaban Tidak Akurat"),
]
ax3.legend(handles=legend_elems, loc="upper left", frameon=False, fontsize=9)

fig.suptitle("Hasil Pengujian Akurasi & Performa Sistem (n = 30 Skenario)",
             fontsize=15, fontweight="bold", y=1.04, color=COLOR_TEXT)

plt.savefig("hasil_pengujian_akurasi_performa.png",
            dpi=200, bbox_inches="tight", facecolor="white")
print("Saved: hasil_pengujian_akurasi_performa.png")