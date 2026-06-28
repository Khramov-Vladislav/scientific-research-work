"""
Графики анализа исходных данных (my_variant_raw.txt).
Файл должен лежать рядом со скриптом.

Запуск:
    python3 plot_raw_data.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.stats import lognorm
import os

os.makedirs("figures", exist_ok=True)

# ── Загрузка ──────────────────────────────────────────────────────────────────
cols = ["JobID","UID","GID","JobName","Partition","NNodes","NTasks","NCPUS","NAlloc",
        "NodeList","Timelimit","Submit","Elapsed_wait","Start","End","Elapsed_str",
        "CPUTimeRaw","AveCPU","ReqMem","AllocMem","State","Extra"]

df = pd.read_csv("my_variant_raw.txt", sep="|", header=None, names=cols)

def parse_hms(s):
    try:
        h, m, sec = str(s).strip().split(":")
        return int(h)*3600 + int(m)*60 + int(sec)
    except Exception:
        return np.nan

df["T_fact_sec"] = df["Elapsed_str"].apply(parse_hms)
df["T_fact_min"] = df["T_fact_sec"] / 60

# ── Параметры оформления ──────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 10,
    "figure.dpi": 150,
})

STATE_COLORS = {
    "COMPLETED":          "#5b9bd5",
    "FAILED":             "#d62728",
    "CANCELLED by 50430": "#ff7f0e",
    "TIMEOUT":            "#9467bd",
    "NODE_FAIL":          "#8c564b",
}
STATE_RU = {
    "COMPLETED":          "COMPLETED",
    "FAILED":             "FAILED",
    "CANCELLED by 50430": "CANCELLED",
    "TIMEOUT":            "TIMEOUT",
    "NODE_FAIL":          "NODE_FAIL",
}

# ═════════════════════════════════════════════════════════════════════════════
# График 1. Распределение по статусам (круговая + столбчатая)
# ═════════════════════════════════════════════════════════════════════════════
state_counts = df["State"].value_counts()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

# --- Круговая ---
labels_ru = [STATE_RU.get(s, s) for s in state_counts.index]
colors    = [STATE_COLORS.get(s, "#aaaaaa") for s in state_counts.index]
wedges, texts, autotexts = ax1.pie(
    state_counts.values,
    labels=labels_ru,
    colors=colors,
    autopct="%1.1f%%",
    startangle=140,
    pctdistance=0.78,
    wedgeprops={"edgecolor": "white", "linewidth": 1.2},
)
for at in autotexts:
    at.set_fontsize(10)
ax1.set_title("а) Распределение заявок по статусам", pad=12)

# --- Столбчатая ---
bars = ax2.bar(
    labels_ru,
    state_counts.values,
    color=colors,
    edgecolor="white",
    linewidth=0.8,
    width=0.55,
)
for bar, val in zip(bars, state_counts.values):
    ax2.text(bar.get_x() + bar.get_width() / 2,
             bar.get_height() + 10,
             str(val),
             ha="center", va="bottom", fontsize=10)
ax2.set_title("б) Количество заявок по статусам", pad=12)
ax2.set_xlabel("Статус задания")
ax2.set_ylabel("Количество заявок")
ax2.set_ylim(0, state_counts.max() * 1.15)
ax2.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
ax2.set_axisbelow(True)

fig.suptitle(
    f"Анализ исходных данных суперкомпьютера (всего заявок: {len(df)})",
    fontsize=13, y=1.01
)
fig.tight_layout()
path1 = "figures/raw_state_distribution.png"
fig.savefig(path1, bbox_inches="tight")
print(f"Сохранён: {path1}")
plt.close(fig)


# ═════════════════════════════════════════════════════════════════════════════
# График 2. Распределение T_факт для COMPLETED заявок
# ═════════════════════════════════════════════════════════════════════════════
completed = df[df["State"] == "COMPLETED"].dropna(subset=["T_fact_min"]).copy()

# Теоретическая кривая (параметры из анализа)
MU_THEORY    = 3.8621
SIGMA_THEORY = 0.8489
SCALE        = 251            # коэффициент масштабирования

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

# --- а) полный диапазон в минутах ---
clip_99 = np.percentile(completed["T_fact_min"], 99)
data_clip = completed.loc[completed["T_fact_min"] <= clip_99, "T_fact_min"]

ax1.hist(data_clip, bins=40, density=True,
         color="#5b9bd5", alpha=0.75, edgecolor="white", linewidth=0.5)
ax1.axvline(completed["T_fact_min"].mean(), color="#d62728",
            linewidth=1.8, linestyle="--",
            label=f"Среднее: {completed['T_fact_min'].mean():.1f} мин")
ax1.axvline(completed["T_fact_min"].median(), color="#ff7f0e",
            linewidth=1.8, linestyle=":",
            label=f"Медиана: {completed['T_fact_min'].median():.1f} мин")
ax1.set_title(f"а) Фактическое время выполнения\n(99-й перцентиль, N={len(completed)})", pad=8)
ax1.set_xlabel(r"$T_{\rm факт}$, мин")
ax1.set_ylabel("Плотность вероятности")
ax1.legend(framealpha=0.9)
ax1.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
ax1.set_axisbelow(True)

# --- б) масштабированный диапазон [1, 43] с ---
T_MIN, T_MAX = 1, 43
data_scaled = completed["T_fact_min"] * 60 / SCALE   # в единицах модели
data_scaled_clip = data_scaled[data_scaled <= T_MAX]

from scipy.stats import truncnorm
mean_t = (T_MIN + T_MAX) / 2
std_t  = (T_MAX - T_MIN) / 4
x_t    = np.linspace(T_MIN - 1, T_MAX + 1, 400)
a, b   = (T_MIN - mean_t) / std_t, (T_MAX - mean_t) / std_t
pdf_trunc = truncnorm.pdf(x_t, a, b, loc=mean_t, scale=std_t)

ax2.hist(data_scaled_clip, bins=np.arange(T_MIN, T_MAX + 2, 2), density=True,
         color="#5b9bd5", alpha=0.75, edgecolor="white", linewidth=0.5,
         label="Исторические данные (масштаб 1:251)")
ax2.plot(x_t, pdf_trunc, color="#1a9641", linewidth=2, linestyle="--",
         label=f"Усечённое N({mean_t:.0f}, {std_t:.1f})\n[{T_MIN}, {T_MAX}] с")
ax2.axvline(T_MIN, color="grey", linewidth=1, linestyle=":")
ax2.axvline(T_MAX, color="grey", linewidth=1, linestyle=":",
            label=f"Границы [{T_MIN}, {T_MAX}] с")
ax2.set_title(f"б) Масштабированное $T_{{\\rm факт}}$\n(коэффициент 1:{SCALE})", pad=8)
ax2.set_xlabel(r"$T_{\rm факт}$, с (масштабированное)")
ax2.set_ylabel("Плотность вероятности")
ax2.set_xlim(0, T_MAX + 2)
ax2.legend(framealpha=0.9)
ax2.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
ax2.set_axisbelow(True)

fig.suptitle(
    r"Распределение фактического времени выполнения $T_{\rm факт}$"
    "\n(исторические данные, только COMPLETED)",
    fontsize=13, y=1.02
)
fig.tight_layout()
path2 = "figures/raw_T_fact_distribution.png"
fig.savefig(path2, bbox_inches="tight")
print(f"Сохранён: {path2}")
plt.close(fig)

print("\nГотово. Файлы в папке figures/")