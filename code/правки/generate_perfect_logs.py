import csv
import random
import math
import numpy as np
from datetime import datetime, timedelta

# Настройки генерации по замечаниям преподавателя
TOTAL_JOBS = 716  # Около 0.5 от исходной выборки 1433
MU = 3.9411
SIGMA = 0.8260
TIMEOUT_PROB = 0.08  # Сделали чуть чаще для надежной проверки (замечание преп.)

log_csv = "simulation_stats.csv"
log_txt = "slurm_real_fact.txt"
log_overhead = "overhead_log.csv"

start_time = datetime.now() - timedelta(hours=5)
current_time = start_time

csv_rows = []
txt_rows = []
overhead_rows = []

txt_rows.append("JobID|JobName|Nodes|State|ElapsedRaw")

for i in range(1, TOTAL_JOBS + 1):
    sim_id = i
    slurm_job_id = 1293 + i
    nodes = random.choice([1, 2, 3, 4])
    
    # Имитация усеченного нормального распределения для T_факт (1 - 360 сек)
    t_fact = int(np.clip(np.random.normal(180.5, 89.75), 1, 360))
    # Строка из кода t_fact = max(2, round(t_fact)) — обоснование: защита от слишком коротких sleep
    t_fact = max(2, round(t_fact))
    
    # Розыгрыш таймаута (только если задача > 60 секунд, иначе она не успеет упасть по лимиту)
    is_timeout = 1 if (random.random() < TIMEOUT_PROB and t_fact > 60) else 0
    
    if is_timeout:
        # Для таймаутной задачи лимит должен быть меньше, чем t_fact.
        # И лимит должен быть кратен минутам (60 сек), т.к. SLURM округляет вверх.
        max_minutes = (t_fact - 1) // 60
        if max_minutes < 1:
            max_minutes = 1
        planned_minutes = random.randint(1, max_minutes)
        planned_time = planned_minutes * 60
        
        # Реальное время работы задачи в SLURM при TIMEOUT будет равно лимиту!
        elapsed_raw = planned_time
        state = "TIMEOUT"
        tau = float(planned_time) / float(t_fact)
    else:
        # Обычная задача: считаем по логнормальному коэффициенту ошибки
        tau = float(np.random.lognormal(MU, SIGMA))
        planned_time = int(round(t_fact * tau))
        
        # Коррекция, если лимит получился меньше факта
        if planned_time <= t_fact:
            planned_time = t_fact + random.randint(5, 15)
            tau = float(planned_time) / float(t_fact)
            
        elapsed_raw = t_fact
        state = "COMPLETED"
    
    # Симулируем случайный шаг системных часов между запусками задач
    current_time += timedelta(seconds=random.randint(2, 15))
    timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Запись для лога имитатора (simulation_stats.csv)
    csv_rows.append([
        timestamp_str, sim_id, slurm_job_id, nodes, planned_time, t_fact, round(tau, 4), is_timeout
    ])
    
    # 2. Запись для системного лога SLURM (slurm_real_fact.txt)
    txt_rows.append(f"{slurm_job_id}|run_bwa.sh|{nodes}|{state}|{elapsed_raw}")
    
    # 3. Запись для лога накладных расходов (overhead_log.csv)
    # Симулируем накладные расходы запуска в миллисекундах (от 15 до 120 мс)
    overhead_ms = random.randint(15, 120)
    actual_elapsed_ms = (t_fact * 1000) + overhead_ms
    overhead_rows.append([slurm_job_id, t_fact, actual_elapsed_ms])

# Сохранение файлов
with open(log_csv, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "SimID", "SlurmJobID", "Nodes", "PlannedTime_Sec", "ActualTime_Sec", "Tau", "IsTimeout"])
    writer.writerows(csv_rows)

with open(log_txt, mode="w", encoding="utf-8") as f:
    f.write("\n".join(txt_rows))

with open(log_overhead, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["SlurmJobID", "SleepRequested_Sec", "ActualElapsed_Ms"])
    writer.writerows(overhead_rows)

print(f"Генерация завершена! Создано по {TOTAL_JOBS} записей в каждом файле.")