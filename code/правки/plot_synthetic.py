"""
Скрипт построения графиков синтетических данных имитатора заявок SLURM.
Генерирует 3 рисунка для вставки в отчёт (раздел 1.4).

Входные файлы (укажите пути ниже):
  simulation_stats.csv  — лог имитатора
  slurm_real_fact.txt   — лог планировщика SLURM
  overhead_log.csv      — лог высокоточного таймера

Выходные файлы (сохраняются рядом со скриптом):
  fig_synthetic_elapsed.png   — рис. A: гистограмма T_факт (синтетика)
  fig_synthetic_ln_tau.png    — рис. B: гистограмма ln(τ) (синтетика vs история)
  fig_synthetic_tau.png       — рис. C: гистограмма τ (синтетика)
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import os

# ── пути к файлам данных ──────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.abspath(__file__))
SIM_CSV   = os.path.join(BASE, "simulation_stats.csv")
SLURM_TXT = os.path.join(BASE, "slurm_real_fact.txt")
OVERHEAD  = os.path.join(BASE, "overhead_log.csv")

# ── параметры исторического датасета (из раздела 1.3 отчёта) ─────────────────
MU_HIST    = 3.9411
SIGMA_HIST = 0.8260

# ── стиль, приближённый к графикам в отчёте ──────────────────────────────────
plt.rcParams.update({
    "font.family":   "DejaVu Sans",
    "font.size":     11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 10,
    "figure.dpi":    150,
    "axes.grid":     True,
    "grid.alpha":    0.3,
})
TEAL = "#3a9e8f"
RED  = "#c0392b"
BLUE = "#2980b9"

# ── загрузка данных ───────────────────────────────────────────────────────────
sim   = pd.read_csv(SIM_CSV)
slurm = pd.read_csv(SLURM_TXT, sep="|")

completed_sim   = sim[sim["IsTimeout"] == 0].copy()
completed_slurm = slurm[slurm["State"] == "COMPLETED"].copy()

t_fact_syn = completed_slurm["ElapsedRaw"].values   # T_факт из лога SLURM
tau_syn    = completed_sim["Tau"].values             # τ из лога имитатора
ln_tau_syn = np.log(tau_syn)

# ── эмпирические параметры, вычисленные из реальных файлов данных ────────────
mu_emp    = float(np.mean(ln_tau_syn))
sigma_emp = float(np.std(ln_tau_syn, ddof=1))
n_comp    = len(t_fact_syn)
t_mean    = float(np.mean(t_fact_syn))
t_std     = float(np.std(t_fact_syn, ddof=1))

print("=" * 60)
print("Значения для отчёта (раздел 1.4):")
print(f"  COMPLETED заявок : {n_comp}")
print(f"  T_факт: min={t_fact_syn.min()} с, max={t_fact_syn.max()} с")
print(f"          mean={t_mean:.2f} с, std={t_std:.2f} с")
print(f"  μ̂  = {mu_emp:.4f}   (историческое μ  = {MU_HIST})")
print(f"  σ̂  = {sigma_emp:.4f}   (историческое σ  = {SIGMA_HIST})")
print(f"  Отклонение μ: {abs(mu_emp - MU_HIST)/MU_HIST*100:.2f}%")
print(f"  Отклонение σ: {abs(sigma_emp - SIGMA_HIST)/SIGMA_HIST*100:.2f}%")
print("=" * 60)

T_MIN, T_MAX = int(t_fact_syn.min()), int(t_fact_syn.max())
mu_t    = (T_MIN + T_MAX) / 2
sigma_t = (T_MAX - T_MIN) / 4

# ═══════════════════════════════════════════════════════════════════════════════
# РИС. A — гистограмма T_факт синтетических данных (COMPLETED)
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 4.5))

bins_t = np.linspace(0, T_MAX + 20, 25)
bin_w  = bins_t[1] - bins_t[0]

ax.hist(t_fact_syn, bins=bins_t,
        color=TEAL, edgecolor="white", linewidth=0.5,
        label=f"Выборка имитатора (n={n_comp})")

a = (T_MIN - mu_t) / sigma_t
b = (T_MAX - mu_t) / sigma_t
rv = stats.truncnorm(a, b, loc=mu_t, scale=sigma_t)
x_t = np.linspace(0, T_MAX + 20, 500)
ax.plot(x_t, rv.pdf(x_t) * n_comp * bin_w,
        color=RED, linewidth=2,
        label=f"Усечённое N(μ={mu_t:.0f}, σ={sigma_t:.1f}), [{T_MIN},{T_MAX}] с")

ax.set_xlabel("Фактическое время выполнения (T_факт), с")
ax.set_ylabel("Количество заявок")
ax.set_title("Распределение фактического времени выполнения\n"
             f"(синтетические данные, COMPLETED, n={n_comp})")
ax.legend()
fig.tight_layout()
out_a = os.path.join(BASE, "fig_synthetic_elapsed.png")
fig.savefig(out_a, bbox_inches="tight")
plt.close(fig)
print(f"Сохранён: {out_a}")

# ═══════════════════════════════════════════════════════════════════════════════
# РИС. B — гистограмма ln(τ) синтетика + кривые исторических и эмпирических
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 4.5))

bins_ln = np.linspace(0, 8, 32)
ax.hist(ln_tau_syn, bins=bins_ln,
        color=TEAL, edgecolor="white", linewidth=0.5,
        density=True,
        label=f"Выборка ln(τ), имитатор (n={n_comp})")

x_ln = np.linspace(0, 8, 500)
ax.plot(x_ln, stats.norm.pdf(x_ln, MU_HIST, SIGMA_HIST),
        color=RED, linewidth=2,
        label=f"N(μ={MU_HIST}, σ={SIGMA_HIST}) — исторические")
ax.plot(x_ln, stats.norm.pdf(x_ln, mu_emp, sigma_emp),
        color=BLUE, linewidth=2, linestyle="--",
        label=f"N(μ̂={mu_emp:.4f}, σ̂={sigma_emp:.4f}) — имитатор")

ax.axvline(MU_HIST, color=RED,  linewidth=1.2, linestyle="--", alpha=0.7)
ax.axvline(mu_emp,  color=BLUE, linewidth=1.2, linestyle=":",  alpha=0.7)

ax.set_xlabel("ln(τ)")
ax.set_ylabel("Плотность вероятности")
ax.set_title("Распределение логарифма коэффициента ошибки оценки ln(τ)\n"
             "(τ = T_заявки / T_факт, синтетические данные, COMPLETED)")
ax.legend()
fig.tight_layout()
out_b = os.path.join(BASE, "fig_synthetic_ln_tau.png")
fig.savefig(out_b, bbox_inches="tight")
plt.close(fig)
print(f"Сохранён: {out_b}")

# ═══════════════════════════════════════════════════════════════════════════════
# РИС. C — гистограмма τ (коэффициент ошибки, линейная шкала)
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 4.5))

tau_clip = tau_syn[tau_syn <= 400]
bins_tau = np.linspace(0, 400, 30)

ax.hist(tau_clip, bins=bins_tau,
        color=TEAL, edgecolor="white", linewidth=0.5,
        density=True,
        label=f"Выборка τ, имитатор (n={len(tau_clip)})")

x_tau = np.linspace(0.5, 400, 1000)
ax.plot(x_tau,
        stats.lognorm.pdf(x_tau, s=SIGMA_HIST, scale=np.exp(MU_HIST)),
        color=RED, linewidth=2,
        label=f"LogNormal(μ={MU_HIST}, σ={SIGMA_HIST}) — исторические")
ax.plot(x_tau,
        stats.lognorm.pdf(x_tau, s=sigma_emp, scale=np.exp(mu_emp)),
        color=BLUE, linewidth=2, linestyle="--",
        label=f"LogNormal(μ̂={mu_emp:.4f}, σ̂={sigma_emp:.4f}) — имитатор")

ax.set_xlabel("Коэффициент ошибки пользователя τ = T_заявки / T_факт")
ax.set_ylabel("Плотность вероятности")
ax.set_title("Распределение коэффициента ошибки оценки τ\n"
             "(синтетические данные, COMPLETED)")
ax.legend()
fig.tight_layout()
out_c = os.path.join(BASE, "fig_synthetic_tau.png")
fig.savefig(out_c, bbox_inches="tight")
plt.close(fig)
print(f"Сохранён: {out_c}")

print("\nВсе графики построены успешно.")