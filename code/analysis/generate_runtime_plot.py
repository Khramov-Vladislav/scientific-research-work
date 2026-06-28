import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Настройка академического стиля под ГОСТ
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'sans-serif',
    'axes.unicode_minus': False
})

# --- ОПРЕДЕЛЕНИЕ ПУТЕЙ К ФАЙЛАМ ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(CODE_DIR, "data")

RAW_FILE = os.path.join(DATA_DIR, "my_variant_raw.txt")
SLURM_FACT_FILE = os.path.join(DATA_DIR, "slurm_real_fact.txt")
OUTPUT_IMAGE = os.path.join(SCRIPT_DIR, "runtime_seconds_distribution.png")

# ==========================================
# 1. ЗАГРУЗКА ИСХОДНЫХ ДАННЫХ (В СЕКУНДАХ)
# ==========================================
raw_runtimes_sec = []

if os.path.exists(RAW_FILE):
    print(f"Парсинг исходных данных из: {RAW_FILE}")
    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) < 21:
                continue
            
            state = parts[20].strip()
            if state == 'COMPLETED':
                try:
                    t_fact_sec = int(parts[17].strip())
                    if t_fact_sec > 0:  # Исключаем чистые нули
                        raw_runtimes_sec.append(t_fact_sec)
                except ValueError:
                    continue
                    
    print(f"-> Успешно загружено {len(raw_runtimes_sec)} исторических строк.")
else:
    print(f"Ошибка: Файл {RAW_FILE} не найден в папке data!")

# ==========================================
# 2. ЗАГРУЗКА ЭМИТИРОВАННЫХ ДАННЫХ (В СЕКУНДАХ)
# ==========================================
sim_runtimes_sec = []

if os.path.exists(SLURM_FACT_FILE):
    print(f"Парсинг эмитированных данных из: {SLURM_FACT_FILE}")
    try:
        df_fact = pd.read_csv(SLURM_FACT_FILE, sep='|')
        df_fact.columns = df_fact.columns.str.strip()
        
        df_completed = df_fact[df_fact['State'] == 'COMPLETED']
        sim_runtimes_sec = df_completed['ElapsedRaw'].values
        print(f"-> Успешно загружено {len(sim_runtimes_sec)} эмитированных задач.")
    except Exception as e:
        print(f"Ошибка чтения файла SLURM: {e}")
else:
    print(f"Ошибка: Файл {SLURM_FACT_FILE} не найден в папке data!")

# ==========================================
# 3. ПОСТРОЕНИЕ ДВОЙНОГО ГРАФИКА
# ==========================================
if len(raw_runtimes_sec) == 0 and len(sim_runtimes_sec) == 0:
    print("Данные для построения отсутствуют.")
    exit(1)

print("Отрисовка двойного графика распределения...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

# --- ЛЕВЫЙ ГРАФИК: Исходные данные с ЛОГАРИФМИЧЕСКОЙ осью X ---
if len(raw_runtimes_sec) > 0:
    # log_scale=True распределит задачи от 1 секунды до 12 часов равномерно
    sns.histplot(raw_runtimes_sec, bins=40, log_scale=True, stat="density", 
                 color="royalblue", alpha=0.6, ax=ax1, label="Реальные логи")
    ax1.set_title("Исходные данные (Логарифмический масштаб)", fontsize=11, pad=8)
    ax1.set_xlabel("Время выполнения задачи ($T_{\\text{факт}}$), секунды (log scale)")
    ax1.set_ylabel("Плотность вероятности")
    ax1.grid(True, linestyle="--", alpha=0.5, which="both") # which="both" для лог-сетки
    ax1.legend()

# --- ПРАВЫЙ ГРАФИК: Эмитированные данные (Обычный масштаб 1-43 сек) ---
if len(sim_runtimes_sec) > 0:
    sns.histplot(sim_runtimes_sec, bins=25, binrange=(1, 43), stat="density", 
                 color="forestgreen", alpha=0.6, ax=ax2, label="Эмуляция в SLURM")
    ax2.set_title("Эмитированные данные (Масштаб симулятора)", fontsize=11, pad=8)
    ax2.set_xlabel("Время выполнения задачи ($T_{\\text{факт}}$), секунды")
    ax2.set_ylabel("Плотность вероятности")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend()

plt.suptitle("Анализ распределений времени выполнения задач в секундах", fontsize=13, y=0.98)
plt.tight_layout()

# Сохранение результата
plt.savefig(OUTPUT_IMAGE, dpi=300)
plt.close()
print(f"Новый график сохранен в: {OUTPUT_IMAGE}")