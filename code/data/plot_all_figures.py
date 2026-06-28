"""
Генерация всех графиков для отчёта по НИР.

Файлы должны лежать рядом со скриптом:
    my_variant_raw.txt
    simulation_stats.csv

Запуск:
    pip install matplotlib numpy pandas scipy
    python3 plot_all_figures.py

Результат — папка figures/ с четырьмя PNG-файлами.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import lognorm, truncnorm
import os

os.makedirs("figures", exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size":        11,
    "axes.titlesize":   12,
    "axes.labelsize":   11,
    "legend.fontsize":  10,
    "figure.dpi":       150,
})

# ── Константы ─────────────────────────────────────────────────────────────────
MU_THEORY    = 3.8621
SIGMA_THEORY = 0.8489
T_MIN, T_MAX = 1, 43
SCALE        = 251
TAU_MAX      = 150
BIN_WIDTH    = 5

# ── Вспомогательная функция ───────────────────────────────────────────────────
def parse_hms(s):
    try:
        h, m, sec = str(s).strip().split(":")
        return int(h) * 3600 + int(m) * 60 + int(sec)
    except Exception:
        return np.nan

# ── Загрузка исторических данных ──────────────────────────────────────────────
cols = ["JobID","UID","GID","JobName","Partition","NNodes","NTasks","NCPUS","NAlloc",
        "NodeList","Timelimit","Submit","Elapsed_wait","Start","End","Elapsed_str",
        "CPUTimeRaw","AveCPU","ReqMem","AllocMem","State","Extra"]

df_raw = pd.read_csv("my_variant_raw.txt", sep="|", header=None, names=cols)
df_raw["T_fact_sec"] = df_raw["Elapsed_str"].apply(parse_hms)
df_raw["T_fact_min"] = df_raw["T_fact_sec"] / 60

hist = df_raw[df_raw["State"] == "COMPLETED"].dropna(subset=["T_fact_sec"]).copy()
hist["Timelimit_sec"] = hist["Timelimit"].apply(parse_hms)
hist = hist[hist["Timelimit_sec"] > 0].copy()
hist["tau"]           = hist["Timelimit_sec"] / hist["T_fact_sec"]
hist["T_fact_scaled"] = hist["T_fact_sec"] / SCALE

# ── Загрузка симулированных данных ────────────────────────────────────────────
sim = pd.read_csv("simulation_stats.csv")
sim_normal = sim[sim["PlannedTime_Sec"] > sim["ActualTime_Sec"]].copy()
sim_normal["tau"] = sim_normal["PlannedTime_Sec"] / sim_normal["ActualTime_Sec"]

hist_tau = hist.loc[hist["tau"] <= TAU_MAX, "tau"]
sim_tau  = sim_normal.loc[sim_normal["tau"] <= TAU_MAX, "tau"]

# ── Теоретические кривые ──────────────────────────────────────────────────────
x_tau  = np.linspace(0.01, TAU_MAX, 1000)
pdf_lognorm = lognorm.pdf(x_tau, s=SIGMA_THEORY, scale=np.exp(MU_THEORY))

mean_t = (T_MIN + T_MAX) / 2
std_t  = (T_MAX - T_MIN) / 4
x_t    = np.linspace(T_MIN - 1, T_MAX + 1, 400)
a, b   = (T_MIN - mean_t) / std_t, (T_MAX - mean_t) / std_t
pdf_trunc = truncnorm.pdf(x_t, a, b, loc=mean_t, scale=std_t)

bins_tau = np.arange(0, TAU_MAX + BIN_WIDTH, BIN_WIDTH)

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
# Рисунок 1а. Статусы исходных данных (столбчатая)
# ═════════════════════════════════════════════════════════════════════════════
df_raw["State_norm"] = df_raw["State"].replace({"CANCELLED by 50430": "CANCELLED"})
raw_counts = df_raw["State_norm"].value_counts()

def bar_chart(ax, counts, title, total):
    labels = counts.index.tolist()
    values = counts.values
    colors = [STATE_COLORS.get(l, "#aaaaaa") for l in labels]
    bars = ax.bar(labels, values, color=colors,
                  edgecolor="white", linewidth=0.8, width=0.5)
    for bar, val in zip(bars, values):
        pct = 100 * val / total
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + total * 0.012,
                f"{val}\n({pct:.1f}%)",
                ha="center", va="bottom", fontsize=10)
    ax.set_title(title, pad=10)
    ax.set_xlabel("Статус задания")
    ax.set_ylabel("Количество заявок")
    ax.set_ylim(0, values.max() * 1.2)
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)

fig, ax = plt.subplots(figsize=(8, 5))
bar_chart(ax, raw_counts,
          f"Распределение заявок по статусам\n"
          f"(исходные данные acct_0921-0923, всего: {len(df_raw)})",
          len(df_raw))
fig.tight_layout()
fig.savefig("figures/fig1a_raw_states.png", bbox_inches="tight")
print("Сохранён: figures/fig1a_raw_states.png")
plt.close(fig)

# ── Рисунок 1б. Статусы данных имитатора ─────────────────────────────────────
sim_counts = pd.Series({
    "COMPLETED": (sim["PlannedTime_Sec"] > sim["ActualTime_Sec"]).sum(),
    "TIMEOUT":   (sim["PlannedTime_Sec"] <= sim["ActualTime_Sec"]).sum(),
})

fig, ax = plt.subplots(figsize=(6, 5))
bar_chart(ax, sim_counts,
          f"Распределение заявок по статусам\n"
          f"(данные имитатора, всего: {len(sim)})",
          len(sim))
fig.tight_layout()
fig.savefig("figures/fig1b_sim_states.png", bbox_inches="tight")
print("Сохранён: figures/fig1b_sim_states.png")
plt.close(fig)


# ═════════════════════════════════════════════════════════════════════════════
# Рисунок 2. T_факт исторических данных + масштабирование
# ═════════════════════════════════════════════════════════════════════════════
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

# а) полный диапазон в минутах (до 99-го перцентиля)
clip_99   = np.percentile(hist["T_fact_min"], 99)
data_clip = hist.loc[hist["T_fact_min"] <= clip_99, "T_fact_min"]

ax1.hist(data_clip, bins=40, density=True,
         color="#5b9bd5", alpha=0.75, edgecolor="white", linewidth=0.5)
ax1.axvline(hist["T_fact_min"].mean(), color="#d62728", linewidth=1.8,
            linestyle="--",
            label=f"Среднее: {hist['T_fact_min'].mean():.1f} мин")
ax1.axvline(hist["T_fact_min"].median(), color="#ff7f0e", linewidth=1.8,
            linestyle=":",
            label=f"Медиана: {hist['T_fact_min'].median():.1f} мин")
ax1.set_title(f"а) Исходный $T_{{\\rm факт}}$ (до 99-го перцентиля)\n"
              f"N={len(hist)}, диапазон: "
              f"{hist['T_fact_min'].min():.0f}–"
              f"{hist['T_fact_min'].max():.0f} мин", pad=8)
ax1.set_xlabel(r"$T_{\rm факт}$, мин")
ax1.set_ylabel("Плотность вероятности")
ax1.legend(framealpha=0.9)
ax1.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
ax1.set_axisbelow(True)

# б) масштабированный диапазон
data_sc = hist.loc[hist["T_fact_scaled"] <= T_MAX, "T_fact_scaled"]
ax2.hist(data_sc, bins=np.arange(T_MIN, T_MAX + 2, 2), density=True,
         color="#5b9bd5", alpha=0.75, edgecolor="white", linewidth=0.5,
         label=f"Исторические данные (масштаб 1:{SCALE})")
ax2.plot(x_t, pdf_trunc, color="#1a9641", linewidth=2, linestyle="--",
         label=f"Усечённое N({mean_t:.0f}, {std_t:.1f}), [{T_MIN}, {T_MAX}] с")
ax2.axvline(T_MIN, color="grey", linewidth=1, linestyle=":")
ax2.axvline(T_MAX, color="grey", linewidth=1, linestyle=":",
            label=f"Границы модели [{T_MIN}, {T_MAX}] с")
ax2.set_title(f"б) Масштабированный $T_{{\\rm факт}}$"
              f" (коэффициент 1:{SCALE})", pad=8)
ax2.set_xlabel(r"$T_{\rm факт}$, с (масштабированное)")
ax2.set_ylabel("Плотность вероятности")
ax2.set_xlim(0, T_MAX + 2)
ax2.legend(framealpha=0.9)
ax2.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
ax2.set_axisbelow(True)

fig.suptitle(
    r"Распределение фактического времени выполнения $T_{\rm факт}$"
    "\n(исторические данные, только COMPLETED)",
    fontsize=12, y=1.02,
)
fig.tight_layout()
fig.savefig("figures/fig2_raw_T_fact_distribution.png", bbox_inches="tight")
print("Сохранён: figures/fig2_raw_T_fact_distribution.png")
plt.close(fig)


# ═════════════════════════════════════════════════════════════════════════════
# Рисунок 3. Распределение τ: история vs симуляция
# ═════════════════════════════════════════════════════════════════════════════
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fig.subplots_adjust(wspace=0.32)

ax1.hist(hist_tau, bins=bins_tau, density=True,
         color="#5b9bd5", alpha=0.75, edgecolor="white", linewidth=0.5,
         label="Исторический факт")
ax1.plot(x_tau, pdf_lognorm, color="#d62728", linewidth=2,
         label=f"Логнормальный закон\n(µ={MU_THEORY}, σ={SIGMA_THEORY})")
ax1.set_title("а) Исходные данные суперкомпьютера", fontsize=12, pad=10)
ax1.set_xlabel("Коэффициент ошибки (Tau = Тзаявки / Тфакт)", fontsize=10)
ax1.set_ylabel("Плотность вероятности", fontsize=10)
ax1.set_xlim(0, TAU_MAX)
ax1.set_ylim(bottom=0)
ax1.legend(loc="upper right", fontsize=9, framealpha=0.9)
ax1.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
ax1.set_axisbelow(True)

ax2.hist(sim_tau, bins=bins_tau, density=True,
         color="#70ad47", alpha=0.75, edgecolor="white", linewidth=0.5,
         label="Данные моделирования")
ax2.plot(x_tau, pdf_lognorm, color="#d62728", linewidth=2,
         label="Теоретический закон")
ax2.set_title("б) Результат работы имитатора", fontsize=12, pad=10)
ax2.set_xlabel("Коэффициент ошибки (Tau = Тзаявки / Тфакт)", fontsize=10)
ax2.set_ylabel("Плотность вероятности", fontsize=10)
ax2.set_xlim(0, TAU_MAX)
ax2.set_ylim(bottom=0)
ax2.legend(loc="upper right", fontsize=9, framealpha=0.9)
ax2.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
ax2.set_axisbelow(True)

fig.savefig("figures/fig3_error_distributions.png", bbox_inches="tight")
print("Сохранён: figures/fig3_error_distributions.png")
plt.close(fig)


# ═════════════════════════════════════════════════════════════════════════════
# Рисунок 4. План vs Факт (scatter): линейный + логарифмический масштаб
# ═════════════════════════════════════════════════════════════════════════════
sim_to   = sim[sim["PlannedTime_Sec"] <= sim["ActualTime_Sec"]]
sim_norm = sim[sim["PlannedTime_Sec"] >  sim["ActualTime_Sec"]]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

# а) линейный
ax1.scatter(sim_norm["ActualTime_Sec"], sim_norm["PlannedTime_Sec"],
            alpha=0.3, s=14, color="#5b9bd5",
            label=f"Нормальные (N={len(sim_norm)})")
ax1.scatter(sim_to["ActualTime_Sec"], sim_to["PlannedTime_Sec"],
            alpha=0.8, s=30, color="#d62728", marker="x",
            label=f"Таймаутные (N={len(sim_to)})")
diag = [0, sim["ActualTime_Sec"].max() + 5]
ax1.plot(diag, diag, "k--", linewidth=1.2,
         label=r"$T_{\rm заявки} = T_{\rm факт}$")
ax1.set_xlabel(r"$T_{\rm факт}$, с")
ax1.set_ylabel(r"$T_{\rm заявки}$ (план), с")
ax1.set_title("а) Линейный масштаб", pad=8)
ax1.set_xlim(0, sim["ActualTime_Sec"].max() + 3)
ax1.set_ylim(0, sim["PlannedTime_Sec"].max() * 1.05)
ax1.legend(framealpha=0.9)
ax1.grid(linestyle="--", linewidth=0.5, alpha=0.5)
ax1.set_axisbelow(True)

# б) логарифмический
ax2.scatter(sim_norm["ActualTime_Sec"], sim_norm["PlannedTime_Sec"],
            alpha=0.3, s=14, color="#5b9bd5",
            label=f"Нормальные (N={len(sim_norm)})")
ax2.scatter(sim_to["ActualTime_Sec"], sim_to["PlannedTime_Sec"],
            alpha=0.8, s=30, color="#d62728", marker="x",
            label=f"Таймаутные (N={len(sim_to)})")
x_diag = np.logspace(np.log10(0.8), np.log10(sim["ActualTime_Sec"].max() + 5), 200)
ax2.plot(x_diag, x_diag, "k--", linewidth=1.2,
         label=r"$T_{\rm заявки} = T_{\rm факт}$")
ax2.set_xscale("log")
ax2.set_yscale("log")
ax2.set_xlabel(r"$T_{\rm факт}$, с (лог. шкала)")
ax2.set_ylabel(r"$T_{\rm заявки}$ (план), с (лог. шкала)")
ax2.set_title("б) Логарифмический масштаб", pad=8)
ax2.legend(framealpha=0.9)
ax2.grid(which="both", linestyle="--", linewidth=0.5, alpha=0.5)
ax2.set_axisbelow(True)

fig.suptitle(
    f"Сопоставление планового и фактического времени выполнения заявок (N={len(sim)})",
    fontsize=12, y=1.01
)
fig.tight_layout()
fig.savefig("figures/fig4_plan_vs_fact.png", bbox_inches="tight")
print("Сохранён: figures/fig4_plan_vs_fact.png")
plt.close(fig)

print("\nВсе графики сохранены в папку figures/")
print("  fig1a_raw_states.png             — статусы исходных данных")
print("  fig1b_sim_states.png             — статусы данных имитатора")
print("  fig2_raw_T_fact_distribution.png — распределение T_факт")
print("  fig3_error_distributions.png     — распределение τ (история vs имитатор)")
print("  fig4_plan_vs_fact.png            — план vs факт (scatter)")