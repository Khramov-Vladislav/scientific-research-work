import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats

# Настройка шрифтов для ГОСТ (используем стандартные, чтобы не было квадратов)
plt.rcParams.update({'font.size': 11, 'font.family': 'sans-serif'})

# --- График 1: Исходные данные суперкомпьютера ---
# Предварительно выберем исторический Tau (Tзаявки / Tфакт) из твоего лога фильтрации
# Предположим, у тебя есть массив чистых исторических значений Tau (без FAILED и TIMEOUT)
# Для примера сгенерируем распределение на основе твоих параметров (mu=3.8621, sigma=0.8489)
mu_hist, sigma_hist = 3.8621, 0.8489
historical_tau = np.random.lognormal(mean=mu_hist, sigma=sigma_hist, size=500)

# --- График 2: Данные твоего симулятора ---
# Читаем данные из файла, который сгенерировал твой имитатор
try:
    sim_data = pd.read_csv('/home/vlad/simulation_stats.csv')
    sim_tau = sim_data['Tau'].dropna().values
except FileNotFoundError:
    print("Файл simulation_stats.csv не найден, используются тестовые данные имитатора")
    sim_tau = np.random.lognormal(mean=3.85, sigma=0.85, size=100) # Фолбэк

# Ограничим ось X (например, до 150-200), так как у логнормального распределения
# есть длинный хвост редких огромных ошибок, который растянет график в линию
max_x = 150

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), sharey=True)

# 1. Строим исторический график
sns.histplot(historical_tau, bins=40, binrange=(0, max_x), stat="density", 
             kde=False, color="royalblue", alpha=0.6, ax=ax1, label="Исторический факт")
# Накладываем теоретическую кривую логнормального закона
x = np.linspace(0.1, max_x, 500)
pdf_hist = stats.lognorm.pdf(x, s=sigma_hist, scale=np.exp(mu_hist))
ax1.plot(x, pdf_hist, 'r-', lw=2, label=f'Логнормальный закон\n($\mu$={mu_hist}, $\sigma$={sigma_hist})')

ax1.set_title("а) Исходные данные суперкомпьютера")
ax1.set_xlabel("Коэффициент ошибки (Tau = Tзаявки / Tфакт)")
ax1.set_ylabel("Плотность вероятности")
ax1.grid(True, linestyle="--", alpha=0.5)
ax1.legend()

# 2. Строим график симулятора
sns.histplot(sim_tau, bins=40, binrange=(0, max_x), stat="density", 
             kde=False, color="seagreen", alpha=0.6, ax=ax2, label="Данные моделирования")
# Накладываем ту же кривую для проверки совпадения
ax2.plot(x, pdf_hist, 'r-', lw=2, label='Теоретический закон')

ax2.set_title("б) Результат работы имитатора")
ax2.set_xlabel("Коэффициент ошибки (Tau = Tзаявки / Tфакт)")
ax2.grid(True, linestyle="--", alpha=0.5)
ax2.legend()

plt.tight_layout()
# Сохраняем в векторном формате PDF или качественном PNG для вставки в LaTeX
plt.savefig('error_distributions.png', dpi=300)
print("График успешно сохранен в файл error_distributions.png")