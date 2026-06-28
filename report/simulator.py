import os
import sys
import random
import math
import csv
import shutil
import subprocess
from datetime import datetime

# --- НАСТРОЙКИ ---
UID = 50430
JOB_NAME = "run_bwa.sh"

# --- МАСШТАБИРОВАННЫЕ ПАРАМЕТРЫ ИЗ ДАТАСЕТА ---
T_MIN = 1
T_MAX = 43

MU = 3.8621
SIGMA = 0.8489
TIMEOUT_RATE = 0.05

def generate_job():
    # 1. Фактическое время по усеченному нормальному распределению
    while True:
        mean_t = (T_MIN + T_MAX) / 2
        std_t = (T_MAX - T_MIN) / 4
        t_fact = random.normalvariate(mean_t, std_t)
        if T_MIN <= t_fact <= T_MAX:
            break

    t_fact = max(2, round(t_fact))  

    # Определяем, будет ли эта задача таймаутом на основе исторической вероятности
    is_timeout = random.random() < TIMEOUT_RATE

    if is_timeout:
        # Режим таймаута: лимит времени строго меньше фактического времени работы
        t_req = random.randint(1, t_fact - 1)
    else:
        # Нормальный режим: логнормальная ошибка перестраховки пользователя
        tau = random.lognormvariate(MU, SIGMA)
        t_req = round(t_fact * tau)

        # Гарантируем, что в нормальном режиме лимит всё-таки больше факта
        if t_req <= t_fact:
            t_req = t_fact + random.randint(5, 15)

    # 3. Выбор количества узлов (Равномерное распределение)
    nodes = random.choice([1, 2, 3, 4])

    return t_fact, t_req, nodes

def submit_to_slurm(job_id, t_fact, t_req, nodes):
    # Форматируем лимит времени в посекундный формат ММ:СС
    # Это заставит SLURM обрубать задачи по таймауту с точностью до секунды
    mm = t_req // 60
    ss = t_req % 60
    timelimit_str = f"{mm:02d}:{ss:02d}"

    sbatch_content = f"""#!/bin/bash
#SBATCH --job-name={JOB_NAME}
#SBATCH --nodes={nodes}
#SBATCH --time={timelimit_str}
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null

sleep {t_fact}
"""
    # Папка, куда будут складываться все сгенерированные скрипты
    jobs_dir = "/home/vlad/saved_jobs"
    script_name = f"job_{job_id:02d}.sh"
    
    with open(script_name, "w") as f:
        f.write(sbatch_content)

    try:
        # Отправляем задачу в SLURM
        result = subprocess.run(["sbatch", script_name], capture_output=True, text=True, check=True)
        slurm_job_id = result.stdout.strip().split()[-1]
        print(f"Заявка {job_id:02d} отправлена. ID: {slurm_job_id} | Лимит: {t_req:2d}с ({timelimit_str}) | Факт: {t_fact:2d}с | Будет TIMEOUT: {t_req < t_fact}")
        
        # Переносим сохраненный скрипт в постоянную папку с указанием Slurm ID
        final_script_name = f"job_{job_id:02d}_slurm_{slurm_job_id}.sh"
        shutil.move(script_name, os.path.join(jobs_dir, final_script_name))
        
        return slurm_job_id
    except Exception as e:
        print(f"Ошибка отправки в SLURM: {e}")
        if os.path.exists(script_name):
            shutil.move(script_name, os.path.join(jobs_dir, f"job_{job_id:02d}_ERROR.sh"))
        return "ERROR"

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

    # Создаем/очищаем папку для скриптов задач перед началом нового эксперимента
    jobs_dir = "/home/vlad/saved_jobs"
    if os.path.exists(jobs_dir):
        shutil.rmtree(jobs_dir)
    os.makedirs(jobs_dir, exist_ok=True)

    log_file = "/home/vlad/simulation_stats.csv"

    # Открываем файл в режиме "w" (перезапись для чистоты эксперимента)
    with open(log_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "SimID", "SlurmJobID", "Nodes", "PlannedTime_Sec", "ActualTime_Sec", "Tau"])

        print(f"--- Запуск генерации {num_jobs} заявок ---")
        for i in range(1, num_jobs + 1):
            t_fact, t_req, nodes = generate_job()
            tau = round(t_req / t_fact, 4)

            slurm_id = submit_to_slurm(i, t_fact, t_req, nodes)
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), i, slurm_id, nodes, t_req, t_fact, tau])

    print(f"--- Имитация завершена. Скрипты сохранены в {jobs_dir} ---")

if __name__ == "__main__":
    main()