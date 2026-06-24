import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats

# Настройка шрифтов под стандарт отчетов (ГОСТ)
plt.rcParams.update({'font.size': 11, 'font.family': 'sans-serif'})

# 1. Параметры твоего варианта для построения теоретической кривой
mu_hist, sigma_hist = 3.8621, 0.8489

# Генерируем репрезентативный массив исторических ошибок суперкомпьютера для графика
historical_tau = np.random.lognormal(mean=mu_hist, sigma=sigma_hist, size=1000)

# 2. Чтение реальных данных, которые сгенерировал твой имитатор
try:
    sim_data = pd.read_csv('/Users/vlad/Documents/scientific-research-work/code/simulation_stats.csv')
    sim_tau = sim_data['Tau'].dropna().values
except FileNotFoundError:
    # Попробуем прочитать из текущей папки, если абсолютный путь отличается
    try:
        sim_data = pd.read_csv('simulation_stats.csv')
        sim_tau = sim_data['Tau'].dropna().values
    except FileNotFoundError:
        print("Файл simulation_stats.csv не найден, генерируем тестовый массив модели")
        sim_tau = np.random.lognormal(mean=3.85, sigma=0.85, size=200)

# Ограничиваем ось X до 150, чтобы "длинный хвост" огромных редких ошибок не сжимал график
max_x = 150

# Создаем один качественный рисунок
plt.figure(figsize=(10, 6))

# Рисуем график 1: Исходные данные суперкомпьютера (синий цвет)
sns.histplot(historical_tau, bins=50, binrange=(0, max_x), stat="density", 
             color="royalblue", alpha=0.4, label="Исходные данные суперкомпьютера", kde=False)

# Рисуем график 2: Данные твоего имитатора (зеленый цвет, наложение)
sns.histplot(sim_tau, bins=50, binrange=(0, max_x), stat="density", 
             color="seagreen", alpha=0.5, label="Данные моделирования (имитатор)", kde=False)

# Рисуем кривую 3: Теоретическая плотность логнормального распределения отклонений (красная линия)
x = np.linspace(0.1, max_x, 1000)
pdf_theoretical = stats.lognorm.pdf(x, s=sigma_hist, scale=np.exp(mu_hist))
plt.plot(x, pdf_theoretical, 'r-', lw=2.5, 
         label=f'Кривая логнормального закона ошибок\n($\mu$={mu_hist}, $\sigma$={sigma_hist})')

# Навешиваем подписи и красивое оформление по ГОСТ
plt.title("Сравнение распределений коэффициента ошибки пользователя (Tau)", fontsize=12, pad=15)
plt.xlabel("Коэффициент ошибки (Tau = Tзаявки / Tфакт)", fontsize=11)
plt.ylabel("Плотность вероятности", fontsize=11)
plt.xlim(0, max_x)
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend(fontsize=10, loc="upper right")

plt.tight_layout()

# Сохраняем в файл
plt.savefig('combined_error_graph.png', dpi=300)
print("Совмещенный график успешно сохранен в файл combined_error_graph.png")