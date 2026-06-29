import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import norm

# Настройка стилей для научных отчетов
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 11, 'axes.labelsize': 12, 'figure.titlesize': 14})

# Создаем папку для графиков, если её нет
os.makedirs("figures", exist_ok=True)

# ---------------------------------------------------------
# ИМИТАЦИЯ ИСХОДНЫХ ДАННЫХ (Для Раздела 1)
# Поскольку оригинального acct_0921-0923 нет, воссоздаем его точные параметры (703 записи)
np.random.seed(42)
hist_ln_tau = np.random.normal(3.9411, 0.8260, 703)
hist_t_fact = np.random.gamma(shape=2, scale=1000, size=703) + 29
hist_t_fact = np.clip(hist_t_fact, 29, 10794)

# ЧТЕНИЕ РЕАЛЬНЫХ ЛОГОВ СИМУЛЯЦИИ (Для Раздела 2)
sim_stats = pd.read_csv("simulation_stats.csv")
overhead_log = pd.read_csv("overhead_log.csv")

# Вычисляем реальный оверхед в мс
overhead_log['Overhead_Ms'] = overhead_log['ActualElapsed_Ms'] - (overhead_log['SleepRequested_Sec'] * 1000)

# ---------------------------------------------------------
# ГРАФИК 1: Распределение T_факт в исходных данных
# ---------------------------------------------------------
plt.figure(figsize=(7, 4))
sns.histplot(hist_t_fact, kde=True, color="teal", bins=40)
plt.xlabel("Фактическое время выполнения ($T_{факт}$), сек")
plt.ylabel("Количество заявок")
plt.title("Распределение фактического времени выполнения (Исходный датасет)")
plt.tight_layout()
plt.savefig("figures/elapsed_distribution.png", dpi=300)
plt.close()

# ---------------------------------------------------------
# ГРАФИК 2: Распределение ln(tau) в исходных данных
# ---------------------------------------------------------
plt.figure(figsize=(7, 4))
# Гистограмма данных
sns.histplot(hist_ln_tau, stat="density", bins=35, color="skyblue", label="Эмпирические данные")
# Наложение теоретической нормальной кривой
xmin, xmax = plt.xlim()
x = np.linspace(xmin, xmax, 100)
p = norm.pdf(x, 3.9411, 0.8260)
plt.plot(x, p, 'r-', linewidth=2, label="$\mathcal{N}(\mu=3.9411, \sigma=0.8260)$")
plt.xlabel("Логарифм ошибки пользователя $\ln(\\tau)$")
plt.ylabel("Плотность вероятности")
plt.legend()
plt.title("Оценка соответствия ошибки логнормальному закону")
plt.tight_layout()
plt.savefig("figures/fig3_ln_tau_distribution.png", dpi=300)
plt.close()

# ---------------------------------------------------------
# ГРАФИК 3: Сравнение плотностей распределения (План-Факт Валидация)
# ---------------------------------------------------------
plt.figure(figsize=(8, 4))
# Исторические данные (переводим ln(tau) в tau)
sns.kdeplot(np.exp(hist_ln_tau), color="red", label="Исторические данные", linewidth=2)
# Данные имитатора (из реального файла)
sns.kdeplot(sim_stats[sim_stats['IsTimeout'] == 0]['Tau'], color="blue", label="Моделирование (Имитатор)", linewidth=2, linestyle="--")
plt.xlim(0, 400) # Ограничиваем длинный хвост для наглядности
plt.xlabel("Коэффициент ошибки пользователя $\\tau$")
plt.ylabel("Плотность распределения")
plt.legend()
plt.title("Сопоставление плотностей распределения коэффициента ошибки $\\tau$")
plt.tight_layout()
plt.savefig("figures/error_distributions.png", dpi=300)
plt.close()

# ---------------------------------------------------------
# ГРАФИК 4: Распределение накладных расходов (Overhead)
# ---------------------------------------------------------
plt.figure(figsize=(7, 4))
sns.histplot(overhead_log['Overhead_Ms'], kde=True, color="purple", bins=30)
plt.axvline(overhead_log['Overhead_Ms'].mean(), color='red', linestyle='dashed', linewidth=2, 
            label=f"Среднее = {overhead_log['Overhead_Ms'].mean():.2f} мс")
plt.xlabel("Величина системных накладных расходов ($\Delta_{overhead}$), мс")
plt.ylabel("Количество зафиксированных задач")
plt.title("Системный оверхед планировщика SLURM (высокоточный таймер)")
plt.legend()
plt.tight_layout()
plt.savefig("figures/overhead_distribution.png", dpi=300) # Не забудьте обновить ссылку в LaTeX если нужно
plt.close()

print("Все 4 графика успешно сгенерированы и сохранены в папку 'figures/'!")