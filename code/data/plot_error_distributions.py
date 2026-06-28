"""
Генерация графика плотности распределения коэффициента ошибки τ.

Файлы рядом со скриптом:
    my_variant_raw.txt
    simulation_stats.csv

Запуск:
    pip install matplotlib numpy pandas scipy
    python3 plot_error_distributions.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import lognorm
import os

# ── Параметры ─────────────────────────────────────────────────────────────────
MU_THEORY    = 3.8621
SIGMA_THEORY = 0.8489
TAU_MAX      = 150
BIN_WIDTH    = 5
OUT_FILE     = "figures/error_distributions.png"

os.makedirs("figures", exist_ok=True)

def parse_hms(s):
    try:
        h, m, sec = str(s).strip().split(":")
        return int(h) * 3600 + int(m) * 60 + int(sec)
    except Exception:
        return np.nan

# ── Исторические данные ───────────────────────────────────────────────────────
cols = ["JobID","UID","GID","JobName","Partition","NNodes","NTasks","NCPUS","NAlloc",
        "NodeList","Timelimit","Submit","Elapsed_wait","Start","End","Elapsed_str",
        "CPUTimeRaw","AveCPU","ReqMem","AllocMem","State","Extra"]

hist_raw = pd.read_csv("my_variant_raw.txt", sep="|", header=None, names=cols)
hist = hist_raw[hist_raw["State"] == "COMPLETED"].copy()
hist["T_fact_sec"]    = hist["Elapsed_str"].apply(parse_hms)
hist["Timelimit_sec"] = hist["Timelimit"].apply(parse_hms)
hist = hist[(hist["T_fact_sec"] > 0) & (hist["Timelimit_sec"] > 0)].copy()
hist["tau"] = hist["Timelimit_sec"] / hist["T_fact_sec"]
# Фильтруем — не обрезаем, а исключаем выбросы за TAU_MAX
hist_tau = hist.loc[hist["tau"] <= TAU_MAX, "tau"]

# ── Симулированные данные ─────────────────────────────────────────────────────
sim = pd.read_csv("simulation_stats.csv")
sim_normal = sim[sim["PlannedTime_Sec"] > sim["ActualTime_Sec"]].copy()
sim_normal["tau"] = sim_normal["PlannedTime_Sec"] / sim_normal["ActualTime_Sec"]
sim_tau = sim_normal.loc[sim_normal["tau"] <= TAU_MAX, "tau"]

print(f"Исторические: всего={len(hist)}, в диапазоне [0,{TAU_MAX}]={len(hist_tau)}")
print(f"Симулированные: всего={len(sim_normal)}, в диапазоне [0,{TAU_MAX}]={len(sim_tau)}")

# ── Теоретическая кривая ──────────────────────────────────────────────────────
x = np.linspace(0.01, TAU_MAX, 1000)
pdf_theory = lognorm.pdf(x, s=SIGMA_THEORY, scale=np.exp(MU_THEORY))

# ── Рисунок ───────────────────────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fig.subplots_adjust(wspace=0.32)

bins = np.arange(0, TAU_MAX + BIN_WIDTH, BIN_WIDTH)

# ---- Левый: исторические ----
ax1.hist(hist_tau, bins=bins, density=True,
         color="#5b9bd5", alpha=0.75, edgecolor="white", linewidth=0.5,
         label="Исторический факт")
ax1.plot(x, pdf_theory, color="#d62728", linewidth=2,
         label=f"Логнормальный закон\n(µ={MU_THEORY}, σ={SIGMA_THEORY})")
ax1.set_title("а) Исходные данные суперкомпьютера", fontsize=12, pad=10)
ax1.set_xlabel("Коэффициент ошибки (Tau = Тзаявки / Тфакт)", fontsize=10)
ax1.set_ylabel("Плотность вероятности", fontsize=10)
ax1.set_xlim(0, TAU_MAX)
ax1.set_ylim(bottom=0)
ax1.legend(loc="upper right", fontsize=9, framealpha=0.9)
ax1.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
ax1.set_axisbelow(True)

# ---- Правый: имитатор ----
ax2.hist(sim_tau, bins=bins, density=True,
         color="#70ad47", alpha=0.75, edgecolor="white", linewidth=0.5,
         label="Данные моделирования")
ax2.plot(x, pdf_theory, color="#d62728", linewidth=2,
         label="Теоретический закон")
ax2.set_title("б) Результат работы имитатора", fontsize=12, pad=10)
ax2.set_xlabel("Коэффициент ошибки (Tau = Тзаявки / Тфакт)", fontsize=10)
ax2.set_ylabel("Плотность вероятности", fontsize=10)
ax2.set_xlim(0, TAU_MAX)
ax2.set_ylim(bottom=0)
ax2.legend(loc="upper right", fontsize=9, framealpha=0.9)
ax2.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
ax2.set_axisbelow(True)

fig.savefig(OUT_FILE, dpi=200, bbox_inches="tight")
print(f"Сохранён: {OUT_FILE}")