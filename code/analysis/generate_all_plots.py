import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats

# Настройка единого академического стиля для отчета (шрифты, сетка)
plt.rcParams.update({
    'font.size': 11, 
    'font.family': 'sans-serif',
    'axes.unicode_minus': False
})

# --- АВТОМАТИЧЕСКОЕ ОПРЕДЕЛЕНИЕ ПУТЕЙ НА MAC ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(CODE_DIR, "data")

# Входные файлы из папки code/data/
RAW_FILE = os.path.join(DATA_DIR, "my_variant_raw.txt")
SIM_STATS_FILE = os.path.join(DATA_DIR, "simulation_stats.csv")
SLURM_FACT_FILE = os.path.join(DATA_DIR, "slurm_real_fact.txt")

# Папка для сохранения готовых картинок (сохраняем прямо в папочку к анализу)
OUTPUT_DIR = SCRIPT_DIR

def parse_time_to_seconds(time_str):
    """Преобразует временную строку формата ЧЧ:ММ:СС в секунды."""
    try:
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return 0
    except:
        return 0

# ==========================================
# ЭТАП 1: Парсинг и масштабирование НАЧАЛЬНЫХ данных
# ==========================================
print(f"Сканирование директории данных: {DATA_DIR}")
print("Парсинг начальных исторических данных из my_variant_raw.txt...")

raw_runtimes_scaled = []
raw_taus = []

if os.path.exists(RAW_FILE):
    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) < 22:
                continue
            
            # Нас интересуют только успешно завершенные задачи для чистой статистики совпадения
            state = parts[21].strip()
            if state == 'COMPLETED':
                t_req_str = parts[10].strip()   # 10-я колонка: Запрошенный лимит времени (TimeLimit)
                t_fact_str = parts[16].strip()  # 16-я колонка: Реальное время выполнения (UsedTime)
                
                t_req = parse_time_to_seconds(t_req_str)
                t_fact = parse_time_to_seconds(t_fact_str)
                
                # Фильтруем задачи-пустышки (меньше 10 секунд в оригинале) и аномалии
                if t_fact > 10 and t_req >= t_fact:
                    # Масштабируем оригинальное время в 1000 раз, как заложено в симуляторе
                    t_fact_scaled = t_fact / 1000.0
                    
                    # Отсекаем по T_MAX = 43 согласно границам усеченного нормального распределения
                    if 1 <= t_fact_scaled <= 43:
                        raw_runtimes_scaled.append(t_fact_scaled)
                        raw_taus.append(t_req / t_fact)
    
    print(f" Успешно обработано {len(raw_runtimes_scaled)} исторических строк.")
else:
    print(f"Ошибка: Файл {RAW_FILE} не найден. Проверь, что перенес его в code/data/")

# ==========================================
# ЭТАП 2: Парсинг и слияние СИМУЛИРОВАННЫХ данных (План + Кластер)
# ==========================================
print("Парсинг результатов симуляции (Слияние План-Факт)...")
sim_runtimes = np.array([])
sim_taus = np.array([])

if os.path.exists(SIM_STATS_FILE) and os.path.exists(SLURM_FACT_FILE):
    try:
        # Читаем математический план генератора
        df_plan = pd.read_csv(SIM_STATS_FILE)
        df_plan.columns = df_plan.columns.str.strip()
        df_plan = df_plan[df_plan['SlurmJobID'] != 'ERROR']
        df_plan['SlurmJobID'] = df_plan['SlurmJobID'].astype(int)
        
        # Читаем лог реального выполнения из SLURM
        df_fact = pd.read_csv(SLURM_FACT_FILE, sep='|')
        df_fact.columns = df_fact.columns.str.strip()
        df_fact['JobID'] = df_fact['JobID'].astype(int)
        
        # Берем только те задачи, которые на кластере вышли в COMPLETED
        df_fact_completed = df_fact[df_fact['State'] == 'COMPLETED']
        
        # Объединяем План и Факт по ID задачи в планировщике
        merged_df = pd.merge(df_plan, df_fact_completed, left_on='SlurmJobID', right_on='JobID', how='inner')
        
        if not merged_df.empty:
            sim_runtimes = merged_df['ElapsedRaw'].values
            # Вычисляем реальный кластерный коэффициент ошибки Tau = План / ElapsedRaw
            merged_df['Tau_Fact'] = merged_df['PlannedTime_Sec'] / merged_df['ElapsedRaw']
            sim_taus = merged_df['Tau_Fact'].values
            print(f" Успешно объединено {len(sim_runtimes)} симулированных задач.")
        else:
            print("Предупреждение: Общие успешно завершенные задачи не найдены при слиянии логов.")
    except Exception as e:
        print(f"Ошибка обработки файлов симуляции: {e}")
else:
    print("Предупреждение: Файлы симуляции отсутствуют в папке data. Проверь запуск на сервере.")

# ==========================================
# ЭТАП 3: Построение верификационных графиков
# ==========================================
print("Отрисовка графиков...")

# --- ГРАФИК 1: Фактическое время выполнения задач ---
plt.figure(figsize=(10, 5))
T_MIN, T_MAX = 1, 43

# Гистограмма начальных (исторических) данных
if len(raw_runtimes_scaled) > 0:
    sns.histplot(raw_runtimes_scaled, bins=25, binrange=(T_MIN, T_MAX), stat="density", 
                 color="royalblue", alpha=0.4, label="Начальные данные (Масштабированные)", kde=False)

# Гистограмма результатов симуляции на кластере SLURM
if len(sim_runtimes) > 0:
    sns.histplot(sim_runtimes, bins=25, binrange=(T_MIN, T_MAX), stat="density", 
                 color="seagreen", alpha=0.5, label="Симулированные данные (Кластер)", kde=False)

# Теоретический эталон: усеченное нормальное распределение
mean_t = (T_MIN + T_MAX) / 2
std_t = (T_MAX - T_MIN) / 4
x_t = np.linspace(T_MIN, T_MAX, 200)
a, b = (T_MIN - mean_t) / std_t, (T_MAX - mean_t) / std_t
plt.plot(x_t, stats.truncnorm.pdf(x_t, a, b, loc=mean_t, scale=std_t), 'r--', lw=2, label='Теоретический закон (TruncNorm)')

plt.title("Сравнение распределений фактического времени выполнения задач ($T_{\\text{факт}}$)", fontsize=12, pad=12)
plt.xlabel("Время выполнения, сек")
plt.ylabel("Плотность вероятности")
plt.xlim(0, T_MAX + 2)
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend(loc='upper right')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'runtime_comparison_graph.png'), dpi=300)
plt.close()


# --- ГРАФИК 2: Ошибка пользователя (Коэффициент Tau) ---
plt.figure(figsize=(10, 5))
MAX_TAU_X = 150  # Обрезаем ось X, чтобы график не растягивался из-за длинного правого хвоста

# Гистограмма начальной исторической ошибки
if len(raw_taus) > 0:
    sns.histplot(raw_taus, bins=60, binrange=(0, MAX_TAU_X), stat="density", 
                 color="royalblue", alpha=0.4, label="Начальные данные (Исторический $\\tau$)", kde=False)

# Гистограмма симулированной ошибки, полученной на твоем кластере
if len(sim_taus) > 0:
    sns.histplot(sim_taus, bins=60, binrange=(0, MAX_TAU_X), stat="density", 
                 color="seagreen", alpha=0.5, label="Симулированные данные (Кластерный $\\tau$)", kde=False)

# Теоретический эталон: логнормальное распределение (параметры из твоего датасета)
mu_th, sigma_th = 3.8621, 0.8489
x_tau = np.linspace(0.1, MAX_TAU_X, 500)
plt.plot(x_tau, stats.lognorm.pdf(x_tau, s=sigma_th, scale=np.exp(mu_th)), 'r--', lw=2, label='Теоретический закон (LogNormal)')

plt.title("Сравнение распределений коэффициента ошибки пользователя ($\\tau = T_{\\text{заявки}} / T_{\\text{факт}}$)", fontsize=12, pad=12)
plt.xlabel("Коэффициент ошибки пользователя (Tau)")
plt.ylabel("Плотность вероятности")
plt.xlim(0, MAX_TAU_X)
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend(loc='upper right')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'error_comparison_graph.png'), dpi=300)
plt.close()

print(f"\n Графики успешно сгенерированы и сохранены в папку {OUTPUT_DIR}:")
print("1. runtime_comparison_graph.png — Сравнение времени выполнения")
print("2. error_comparison_graph.png   — Сравнение ошибок пользователя (Tau)")