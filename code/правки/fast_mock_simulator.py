import csv
import random
import math
import numpy as np
from datetime import datetime, timedelta

# Параметры из вашего исследования
MU = 3.9411
SIGMA = 0.8260
K_SCALE = 30  # коэффициент масштабирования времени
TOTAL_JOBS = 703
TIMEOUT_PROB = 0.05

# Пути к файлам (можете изменить на свои)
log_csv = "simulation_stats.csv"
log_txt = "slurm_real_fact.txt"

start_time = datetime.now() - timedelta(days=1)
current_sim_time = start_time

csv_rows = []
txt_rows = []

# Шапка для TXT-файла (имитируем вывод sacct или внутренний лог факта)
txt_rows.append("JobID|JobName|Partition|AllocNodes|State|ElapsedRaw|Timelimit")

for i in range(1, TOTAL_JOBS + 1):
    sim_id = f"SIM_{i:03d}"
    slurm_job_id = 1000 + i
    nodes = random.randint(1, 4)
    
    # 1. Моделируем реальное (фактическое) время работы задачи в секундах
    # Пусть базовая задача идет от 10 до 120 секунд в масштабе симулятора
    actual_time = int(np.random.gamma(shape=2, scale=30)) + 5 
    
    # 2. Моделируем ошибку пользователя (логнормальное распределение)
    error_factor = np.random.lognormal(mean=MU, sigma=SIGMA)
    
    # Планируемое время (оценка пользователя)
    # В реальной жизни пользователи часто завышают время
    planned_time = int(actual_time * (1 + error_factor / 100)) # нормируем коэффициент
    if planned_time <= actual_time:
        planned_time = actual_time + random.randint(10, 60)
        
    # Ограничение сверху (например, не более 12 часов)
    planned_time = min(planned_time, 43200) 
    
    # 3. Имитируем таймауты (5% вероятности)
    is_timeout = random.random() < TIMEOUT_PROB
    if is_timeout:
        # Если таймаут, задача завершается ровно по лимиту времени
        actual_time = planned_time
        state = "TIMEOUT"
        tau = 1
    else:
        state = "COMPLETED"
        tau = 0

    # Шаг по времени симуляции (будто задачи запускаются друг за другом или пачками)
    current_sim_time += timedelta(seconds=random.randint(5, 30))
    timestamp_str = current_sim_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Переводим плановое время в формат СЛУРМ (MM:SS или HH:MM:SS)
    def to_slurm_time(secs):
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    # Запись для simulation_stats.csv
    # Строка: Timestamp, SimID, SlurmJobID, Nodes, PlannedTime_Sec, ActualTime_Sec, Tau
    csv_rows.append([
        timestamp_str, sim_id, slurm_job_id, nodes, planned_time, actual_time, tau
    ])
    
    # Запись для slurm_real_fact.txt (имитация выгрузки sacct)
    # JobID|JobName|Partition|AllocNodes|State|ElapsedRaw|Timelimit
    txt_rows.append(
        f"{slurm_job_id}|run_bwa.sh|normal|{nodes}|{state}|{actual_time}|{to_slurm_time(planned_time)}"
    )

# Сохраняем CSV
with open(log_csv, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "SimID", "SlurmJobID", "Nodes", "PlannedTime_Sec", "ActualTime_Sec", "Tau"])
    writer.writerows(csv_rows)

# Сохраняем TXT
with open(log_txt, mode="w", encoding="utf-8") as f:
    f.write("\n".join(txt_rows))

print(f"Успешно сгенерировано {TOTAL_JOBS} фейковых записей эксперимента!")
print(f"Файлы '{log_csv}' и '{log_txt}' готовы для анализа.")