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
SIM_STATS_FILE = os.path.join(DATA_DIR, "simulation_stats.csv")
OUTPUT_IMAGE = os.path.join(SCRIPT_DIR, "error_distribution.png")

def parse_time_to_seconds(time_str):
    """Конвертирует строку ЧЧ:ММ:СС в секунды."""
    try:
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return 0
    except:
        return 0

# ==========================================
# 1. РАСЧЕТ TAU ДЛЯ ИСХОДНЫХ ДАННЫХ
# ==========================================
raw_taus = []

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
                    t_req_sec = parse_time_to_seconds(parts[10].strip()) # Лимит (Слот 10)
                    t_fact_sec = int(parts[17].strip())                  # Факт (Слот 17)
                    
                    if t_fact_sec > 0 and t_req_sec >= t_fact_sec:
                        tau = t_req_sec / t_fact_sec
                        raw_taus.append(tau)
                except (ValueError, IndexError):
                    continue
                    
    print(f"-> Успешно рассчитано {len(raw_taus)} значений Tau для истории.")
else:
    print(f"Ошибка: Файл {RAW_FILE} не найден!")

# ==========================================
# 2. СБОР TAU ДЛЯ ИМИТИРОВАННЫХ ДАННЫХ
# ==========================================
sim_taus = []

if os.path.exists(SIM_STATS_FILE):
    print(f"Парсинг имитированных данных из: {SIM_STATS_FILE}")
    try:
        df_sim = pd.read_csv(SIM_STATS_FILE)
        df_sim.columns = df_sim.columns.str.strip()
        
        df_sim = df_sim[df_sim['Tau'] != 'ERROR']
        sim_taus = df_sim['Tau'].astype(float).values
        print(f"-> Успешно загружено {len(sim_taus)} значений Tau из симуляции.")
    except Exception as e:
        print(f"Ошибка чтения файла симуляции: {e}")
else:
    print(f"Ошибка: Файл {SIM_STATS_FILE} не найден!")

# ==========================================
# 3. ПОСТРОЕНИЕ ДВОЙНОГО ГРАФИКА ОШИБКИ C ОГИБАЮЩЕЙ
# ==========================================
if len(raw_taus) == 0 and len(sim_taus) == 0:
    print("Данные для построения отсутствуют.")
    exit(1)

print("Отрисовка графиков ошибки пользователя с огибающими линиями...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

# --- ЛЕВЫЙ ГРАФИК: Исходные данные (Логарифмическая ось X + KDE) ---
if len(raw_taus) > 0:
    sns.histplot(raw_taus, bins=50, log_scale=True, stat="density", 
                 color="royalblue", alpha=0.5, ax=ax1, label="Реальный лог",
                 kde=True, line_kws={"color": "crimson", "linewidth": 2, "linestyle": "-"})
    ax1.set_title("Коэффициент ошибки в исходных данных", fontsize=11, pad=8)
    ax1.set_xlabel("Коэффициент ошибки $\\tau = T_{\\text{заявки}} / T_{\\text{факт}}$ (log scale)")
    ax1.set_ylabel("Плотность вероятности")
    ax1.grid(True, linestyle="--", alpha=0.5, which="both")
    ax1.legend()

# --- ПРАВЫЙ ГРАФИК: Имитированные данные (Логарифмическая ось X + KDE) ---
if len(sim_taus) > 0:
    sns.histplot(sim_taus, bins=50, log_scale=True, stat="density", 
                 color="forestgreen", alpha=0.5, ax=ax2, label="Генерация (Симулятор)",
                 kde=True, line_kws={"color": "crimson", "linewidth": 2, "linestyle": "-"})
    ax2.set_title("Коэффициент ошибки в имитированных данных", fontsize=11, pad=8)
    ax2.set_xlabel("Коэффициент ошибки $\\tau = T_{\\text{план}} / T_{\\text{факт}}$ (log scale)")
    ax2.set_ylabel("Плотность вероятности")
    ax2.grid(True, linestyle="--", alpha=0.5, which="both")
    ax2.legend()

plt.suptitle("Сравнение распределений коэффициента ошибки пользователя (Tau) с огибающей плотности", fontsize=13, y=0.98)
plt.tight_layout()

# Сохранение результата
plt.savefig(OUTPUT_IMAGE, dpi=300)
plt.close()
print(f"График с огибающей успешно сохранен в: {OUTPUT_IMAGE}")