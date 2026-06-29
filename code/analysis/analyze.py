"""
analyze.py — статистический анализ исходной выборки датасета acct_0921-0923
(UID=50430, JobName=run_bwa.sh).

Выполняет:
  1. Фильтрацию и очистку данных.
  2. Вычисление границ T_min, T_max и параметров μ, σ логнормального
     распределения коэффициента ошибки оценки времени τ = T_заявки / T_факт.
  3. Построение трёх графиков для включения в отчёт:
       - Рис. 1: распределение задач по статусам завершения;
       - Рис. 2: гистограмма фактического времени выполнения (логарифмическая шкала);
       - Рис. 3: гистограмма ln(τ) с наложенной кривой нормального распределения.

Использование:
  python3 analyze.py [путь_к_файлу_данных]
  По умолчанию: ./my_variant_raw.txt
"""

import math
import sys
import os
from collections import Counter

# Matplotlib импортируем только если доступен (для серверной среды без GUI)
try:
    import matplotlib
    matplotlib.use("Agg")  # безголовый backend — не требует дисплея
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    PLOT_AVAILABLE = True
except ImportError:
    PLOT_AVAILABLE = False
    print("Предупреждение: matplotlib не установлен. Графики построены не будут.")


# ---------------------------------------------------------------------------
# 1. Чтение и разбор данных
# ---------------------------------------------------------------------------

data_path = sys.argv[1] if len(sys.argv) > 1 else "./my_variant_raw.txt"

if not os.path.exists(data_path):
    print(f"Ошибка: файл '{data_path}' не найден.")
    sys.exit(1)

with open(data_path, "r") as f:
    lines = f.readlines()

# Счётчики и накопители
status_counter   = Counter()   # все строки по статусу
elapsed_all      = []          # ElapsedRaw всех принятых к анализу записей
elapsed_completed = []         # ElapsedRaw только COMPLETED
tau_list          = []         # τ = T_req / T_fact для COMPLETED
total_valid       = 0
timeout_count     = 0

for line in lines:
    parts = line.strip().split("|")
    if len(parts) < 21:
        continue

    try:
        state        = parts[20].strip()
        elapsed_raw  = int(parts[17])    # ElapsedRaw, сек
        timelimit_raw = int(parts[18])   # TimelimitRaw, мин
    except (ValueError, IndexError):
        continue

    # Нормализуем статус (убираем суффикс «by <uid>» у CANCELLED)
    state_key = state.split()[0]
    status_counter[state_key] += 1

    # Отсекаем мгновенные сбои (< 10 с) — они не несут информации о нагрузке
    if elapsed_raw <= 10:
        continue

    # Исключаем записи с ошибками узла и отменённые — они не характеризуют
    # пользовательскую нагрузку, а отражают системные сбои
    if state_key in ("FAILED", "NODE_FAIL", "CANCELLED"):
        continue

    total_valid += 1
    elapsed_all.append(elapsed_raw)

    if state_key == "TIMEOUT":
        timeout_count += 1
        # Таймаутные задачи исключаются из расчёта τ:
        # их фактическое время усечено планировщиком, а не определено задачей
        continue

    # COMPLETED: вычисляем коэффициент ошибки оценки времени
    t_fact = elapsed_raw
    t_req  = timelimit_raw * 60  # TimelimitRaw в минутах → секунды
    tau    = t_req / t_fact

    elapsed_completed.append(t_fact)
    tau_list.append(tau)


# ---------------------------------------------------------------------------
# 2. Вычисление статистических параметров
# ---------------------------------------------------------------------------

if not elapsed_completed:
    print("Ошибка: не найдено ни одной подходящей COMPLETED-записи.")
    sys.exit(1)

n          = len(elapsed_completed)
t_min      = min(elapsed_completed)
t_max      = max(elapsed_completed)
t_mean     = sum(elapsed_completed) / n
vals_sorted = sorted(elapsed_completed)
t_median   = vals_sorted[n // 2]

log_taus = [math.log(t) for t in tau_list]
mu       = sum(log_taus) / n
variance = sum((x - mu) ** 2 for x in log_taus) / n
sigma    = math.sqrt(variance)

timeout_rate = timeout_count / total_valid if total_valid > 0 else 0

# Масштабирование для стенда
K_SCALE  = 30
t_min_sc = max(1, round(t_min / K_SCALE))
t_max_sc = round(t_max / K_SCALE)
t_med_sc = round(t_median / K_SCALE)

print("=" * 55)
print("  РЕЗУЛЬТАТЫ АНАЛИЗА ДАТАСЕТА acct_0921-0923")
print(f"  Вариант: UID=50430, JobName=run_bwa.sh")
print("=" * 55)
print(f"  Всего строк в файле:            {len(lines)}")
print(f"  Принято к анализу (> 10 с):     {total_valid}")
print(f"  Из них COMPLETED:               {n}")
print(f"  Из них TIMEOUT:                 {timeout_count}")
print()
print("  --- Фактическое время выполнения (COMPLETED) ---")
print(f"  T_min:    {t_min:>8} с  ({t_min/60:.1f} мин)")
print(f"  T_max:    {t_max:>8} с  ({t_max/3600:.2f} ч)")
print(f"  Среднее:  {t_mean:>8.0f} с  ({t_mean/60:.1f} мин)")
print(f"  Медиана:  {t_median:>8} с  ({t_median/60:.1f} мин)")
print()
print("  --- Параметры ln(τ),  τ = T_заявки / T_факт ---")
print(f"  μ (среднее ln τ):     {mu:.4f}")
print(f"  σ (стд. откл. ln τ):  {sigma:.4f}")
print(f"  Медиана τ = e^μ:      {math.exp(mu):.1f}×")
print()
print(f"  Доля TIMEOUT-задач:   {timeout_rate*100:.2f}%")
print()
print(f"  --- Масштабирование (k = {K_SCALE}) ---")
print(f"  T_MIN (стенд):  {t_min_sc} с")
print(f"  T_MAX (стенд):  {t_max_sc} с  ({t_max_sc//60} мин {t_max_sc%60} сек)")
print(f"  Медиана (стенд): {t_med_sc} с")
print("=" * 55)


# ---------------------------------------------------------------------------
# 3. Построение графиков
# ---------------------------------------------------------------------------

if not PLOT_AVAILABLE:
    sys.exit(0)

FIG_DIR = "."
os.makedirs(FIG_DIR, exist_ok=True)


# -- Рис. 1: Распределение задач по статусам ---------------------------------

fig1, ax1 = plt.subplots(figsize=(8, 5))

total_all = sum(status_counter.values())
labels    = list(status_counter.keys())
counts    = [status_counter[l] for l in labels]
colors    = {"COMPLETED": "#4878CF", "FAILED": "#6ACC65",
             "CANCELLED": "#D65F5F", "TIMEOUT": "#B47CC7",
             "NODE_FAIL": "#C4AD66"}
bar_colors = [colors.get(l, "#888888") for l in labels]

bars = ax1.bar(labels, counts, color=bar_colors, edgecolor="white", linewidth=0.8)

for bar, cnt in zip(bars, counts):
    pct = cnt / total_all * 100
    ax1.text(bar.get_x() + bar.get_width() / 2,
             bar.get_height() + total_all * 0.005,
             f"{cnt}\n({pct:.1f}%)",
             ha="center", va="bottom", fontsize=9)

ax1.set_title(
    f"Распределение заявок по статусам\n"
    f"(исходные данные acct_0921-0923, всего: {total_all})",
    fontsize=11, pad=12
)
ax1.set_xlabel("Статус задания", fontsize=10)
ax1.set_ylabel("Количество заявок", fontsize=10)
ax1.set_ylim(0, max(counts) * 1.18)
ax1.grid(axis="y", linestyle="--", alpha=0.4)
ax1.spines[["top", "right"]].set_visible(False)

fig1.tight_layout()
path1 = os.path.join(FIG_DIR, "fig1_status_distribution.png")
fig1.savefig(path1, dpi=150)
plt.close(fig1)
print(f"  Рис. 1 сохранён: {path1}")


# -- Рис. 2: Гистограмма ElapsedRaw (лог. шкала) ----------------------------

fig2, ax2 = plt.subplots(figsize=(9, 5))

# Логарифмические бины от 10 с до T_max
log_min = math.log10(10)
log_max = math.log10(t_max * 1.05)
bins    = [10 ** (log_min + (log_max - log_min) * i / 30) for i in range(31)]

ax2.hist(elapsed_completed, bins=bins, color="#5B8DB8", edgecolor="white",
         linewidth=0.5, alpha=0.85)

ax2.axvline(t_min,    color="#CC3333", linestyle="--", linewidth=1.3,
            label=f"T_min = {t_min} с")
ax2.axvline(t_max,    color="#CC3333", linestyle="--", linewidth=1.3,
            label=f"T_max = {t_max} с")
ax2.axvline(t_median, color="#336699", linestyle=":",  linewidth=1.5,
            label=f"медиана = {t_median} с")

ax2.set_xscale("log")
ax2.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax2.set_title(
    "Распределение фактического времени выполнения\n"
    "(выборка acct_0921-0923, COMPLETED, > 10 с)",
    fontsize=11, pad=12
)
ax2.set_xlabel("T_факт, с (логарифмическая шкала)", fontsize=10)
ax2.set_ylabel("Количество заявок", fontsize=10)
ax2.legend(fontsize=9)
ax2.grid(axis="y", linestyle="--", alpha=0.4)
ax2.spines[["top", "right"]].set_visible(False)

fig2.tight_layout()
path2 = os.path.join(FIG_DIR, "fig2_elapsed_distribution.png")
fig2.savefig(path2, dpi=150)
plt.close(fig2)
print(f"  Рис. 2 сохранён: {path2}")


# -- Рис. 3: Гистограмма ln(τ) с наложенной нормальной кривой ---------------

fig3, ax3 = plt.subplots(figsize=(9, 5))

# Гистограмма (плотность вероятности)
ax3.hist(log_taus, bins=40, density=True,
         color="#5B8DB8", edgecolor="white", linewidth=0.5,
         alpha=0.75, label="Выборка ln(τ)")

# Теоретическая кривая нормального распределения
x_lo = mu - 4 * sigma
x_hi = mu + 4 * sigma
xs   = [x_lo + (x_hi - x_lo) * i / 400 for i in range(401)]
ys   = [math.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
        for x in xs]
ax3.plot(xs, ys, color="#CC3333", linewidth=2,
         label=f"N(μ={mu:.4f}, σ={sigma:.4f})")

ax3.axvline(mu, color="#CC3333", linestyle="--", linewidth=1.2,
            label=f"μ = {mu:.4f}")
ax3.axvline(mu - sigma, color="#888888", linestyle=":", linewidth=1,
            label=f"μ ± σ")
ax3.axvline(mu + sigma, color="#888888", linestyle=":", linewidth=1)

ax3.set_title(
    "Распределение логарифма коэффициента ошибки оценки ln(τ)\n"
    "(τ = T_заявки / T_факт, выборка acct_0921-0923, COMPLETED)",
    fontsize=11, pad=12
)
ax3.set_xlabel("ln(τ)", fontsize=10)
ax3.set_ylabel("Плотность вероятности", fontsize=10)
ax3.legend(fontsize=9)
ax3.grid(axis="y", linestyle="--", alpha=0.4)
ax3.spines[["top", "right"]].set_visible(False)

fig3.tight_layout()
path3 = os.path.join(FIG_DIR, "fig3_ln_tau_distribution.png")
fig3.savefig(path3, dpi=150)
plt.close(fig3)
print(f"  Рис. 3 сохранён: {path3}")

print()
print("Готово. Все графики сохранены.")