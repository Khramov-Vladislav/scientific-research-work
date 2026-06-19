import os
import sys
import random
import math
import csv
import subprocess
from datetime import datetime

# --- НАСТРОЙКИ ---
UID = 50430
JOB_NAME = "run_bwa.sh"

# --- МАСШТАБИРОВАННЫЕ ПАРАМЕТРЫ ИЗ ДАТАСЕТА ---
T_MIN = 1       # Масштабированный минимум (26 сек / 1000)
T_MAX = 43      # Масштабированный максимум (43209 сек / 1000)

# Параметры распределения ошибки
MU = 3.8621
SIGMA = 0.8489

def generate_job():
    # 1. Фактическое время по нормальному распределению (с отсечением границ)
    while True:
        mean_t = (T_MIN + T_MAX) / 2
        std_t = (T_MAX - T_MIN) / 4  # 95% значений ложится в диапазон
        t_fact = random.normalvariate(mean_t, std_t)
        if T_MIN <= t_fact <= T_MAX:
            break

    t_fact = max(1, round(t_fact)) # Гарантируем хотя бы 1 секунду сна

    # 2. Пользовательская оценка времени через Логнормальное распределение (Tau)
    tau = random.lognormvariate(MU, SIGMA)
    t_req = round(t_fact * tau)

    # Защитный лимит: SLURM убьет задачу, если лимит меньше факта
    if t_req <= t_fact:
        t_req = t_fact + random.randint(5, 15)

    # 3. Выбор количества узлов {1, 2, 3, 4} (Равномерное распределение)
    nodes = random.choice([1, 2, 3, 4])

    return t_fact, t_req, nodes

def submit_to_slurm(job_id, t_fact, t_req, nodes):
    # Переводим t_req (секунды) в формат SLURM Timelimit (минуты:секунды)
    # Перевод в минуты с округлением вверх (минимум 1 минута для стабильности диспетчера)
    minutes = max(1, math.ceil(t_req / 60))
    timelimit_str = f"{minutes}:00"

    # Формируем скрипт пакетной задачи
    sbatch_content = f"""#!/bin/bash
#SBATCH --job-name={JOB_NAME}
#SBATCH --nodes={nodes}
#SBATCH --time={timelimit_str}
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null

sleep {t_fact}
"""
    script_name = f"job_{job_id}.sh"
    with open(script_name, "w") as f:
        f.write(sbatch_content)

    # Отправляем задачу в очередь SLURM
    try:
        result = subprocess.run(["sbatch", script_name], capture_output=True, text=True, check=True)
        slurm_job_id = result.stdout.strip().split()[-1]
        print(f"Заявка {job_id} отправлена. ID: {slurm_job_id} | Узлов: {nodes} | План (Лимит): {t_req}с | Факт (Сон): {t_fact}с")
        return slurm_job_id
    except Exception as e:
        print(f"Ошибка отправки в SLURM: {e}")
        return "ERROR"
    finally:
        if os.path.exists(script_name):
            os.remove(script_name)

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 simulator.py <количество_заявок>")
        sys.exit(1)

    try:
        num_jobs = int(sys.argv[1])
        if not (1 <= num_jobs <= 999):
            raise ValueError
    except ValueError:
        print("Ошибка: Количество заявок должно быть целым числом от 1 до 999.")
        sys.exit(1)

    log_file = "/home/vlad/simulation_stats.csv"
    file_exists = os.path.isfile(log_file)

    with open(log_file, mode="a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "SimID", "SlurmJobID", "Nodes", "PlannedTime_Sec", "ActualTime_Sec", "Tau"])

        print(f"--- Запуск генерации {num_jobs} заявок ---")
        for i in range(1, num_jobs + 1):
            t_fact, t_req, nodes = generate_job()
            tau = round(t_req / t_fact, 4)

            # Ставим задачу в реальную очередь кластера
            slurm_id = submit_to_slurm(i, t_fact, t_req, nodes)

            # Логируем метаданные в файл "План-Факт"
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), i, slurm_id, nodes, t_req, t_fact, tau])

    print(f"--- Имитация завершена. Статистика сохранена в {log_file} ---")

if __name__ == "__main__":
    main()