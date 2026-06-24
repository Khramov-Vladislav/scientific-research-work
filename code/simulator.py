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

# --- МАСШТАБИРОВАННЫЕ ПАРАМЕТРЫ ИЗ ДАТАСЕТА (ОБНОВИ ИХ ПОСЛЕ ЗАПУСКА СКРИПТА 1) ---
T_MIN = 1       
T_MAX = 43      

# Вставь сюда новые коэффициенты, которые выдаст первая программа:
MU = 3.5214       
SIGMA = 0.7241  
TIMEOUT_RATE = 0.05  # СЮДА ДОЛЮ ТАЙМАУТОВ (например, если 5%, то 0.05)

def generate_job():
    # 1. Фактическое время по нормальному распределению
    while True:
        mean_t = (T_MIN + T_MAX) / 2
        std_t = (T_MAX - T_MIN) / 4
        t_fact = random.normalvariate(mean_t, std_t)
        if T_MIN <= t_fact <= T_MAX:
            break

    t_fact = max(2, round(t_fact)) # Минимум 2 секунды

    # Определяем, будет ли эта задача таймаутом на основе статистики
    is_timeout = random.random() < TIMEOUT_RATE

    if is_timeout:
        # Ситуация таймаута: пользователь запросил МЕНЬШЕ, чем идет задача
        # Лимит времени ставится меньше, чем t_fact
        t_req = random.randint(1, t_fact - 1)
    else:
        # Обычная корректная задача (Логнормальное распределение)
        tau = random.lognormvariate(MU, SIGMA)
        t_req = round(t_fact * tau)
        
        # Гарантируем, что в нормальном режиме лимит все-таки больше факта
        if t_req <= t_fact:
            t_req = t_fact + random.randint(5, 15)

    # 3. Выбор количества узлов (Равномерное распределение)
    nodes = random.choice([1, 2, 3, 4])

    return t_fact, t_req, nodes

def submit_to_slurm(job_id, t_fact, t_req, nodes):
    # Переводим t_req в формат минут для SLURM
    minutes = max(1, math.ceil(t_req / 60))
    timelimit_str = f"{minutes}:00"

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

    try:
        result = subprocess.run(["sbatch", script_name], capture_output=True, text=True, check=True)
        slurm_job_id = result.stdout.strip().split()[-1]
        print(f"Заявка {job_id} отправлена. ID: {slurm_job_id} | Лимит: {t_req}с | Факт: {t_fact}с | Сбой по лимиту: {t_req < t_fact}")
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

        print(f"--- Запуск генерации {num_jobs} заявок с учетом таймаутов ---")
        for i in range(1, num_jobs + 1):
            t_fact, t_req, nodes = generate_job()
            tau = round(t_req / t_fact, 4)

            slurm_id = submit_to_slurm(i, t_fact, t_req, nodes)
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), i, slurm_id, nodes, t_req, t_fact, tau])

    print(f"--- Имитация завершена. Статистика сохранена в {log_file} ---")

if __name__ == "__main__":
    main()