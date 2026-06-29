import os
import sys
import random
import math
import csv
import shutil
import subprocess
from datetime import datetime

UID = 50430
JOB_NAME = "run_bwa.sh"

K_SCALE = 30
T_MIN = 1   
T_MAX = 360 

MU    = 3.9411
SIGMA = 0.8260

TIMEOUT_RATE = 0.05

HOME_DIR  = "/home/vlad"
JOBS_DIR  = f"{HOME_DIR}/saved_jobs"
LOG_FILE  = f"{HOME_DIR}/simulation_stats.csv"


def generate_job():
    mean_t = (T_MIN + T_MAX) / 2   # 180.5 сек
    std_t  = (T_MAX - T_MIN) / 4   # 89.75 сек
    while True:
        t_fact = random.normalvariate(mean_t, std_t)
        if T_MIN <= t_fact <= T_MAX:
            break
    t_fact = round(t_fact)

    is_timeout = random.random() < TIMEOUT_RATE

    if is_timeout:
        if t_fact > 60:
            max_minutes = (t_fact - 1) // 60  # кол-во полных минут
            if max_minutes >= 1:
                limit_minutes = random.randint(1, max_minutes)
            else:
                limit_minutes = 1
            t_req = limit_minutes * 60  
        else:
            is_timeout = False

    if not is_timeout:
        tau   = random.lognormvariate(MU, SIGMA)
        t_req = round(t_fact * tau)
        if t_req <= t_fact:
            t_req = t_fact + random.randint(5, 15)
    nodes = random.choice([1, 2, 3, 4])

    return t_fact, t_req, nodes, is_timeout


def format_timelimit(t_req_sec):
    mm = t_req_sec // 60
    ss = t_req_sec % 60
    return f"{mm:02d}:{ss:02d}"


def submit_to_slurm(job_id, t_fact, t_req, nodes):
    timelimit_str = format_timelimit(t_req)

    sbatch_content = f"""#!/bin/bash
#SBATCH --job-name={JOB_NAME}
#SBATCH --nodes={nodes}
#SBATCH --time={timelimit_str}
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null

# Замер времени с точностью до миллисекунды для анализа накладных расходов SLURM
_START_MS=$(date +%s%3N)
sleep {t_fact}
_END_MS=$(date +%s%3N)
_ELAPSED_MS=$((_END_MS - _START_MS))

# Запись в лог накладных расходов: JobID, запрошенный sleep (с), реальное время (мс)
echo "${{SLURM_JOB_ID}},{t_fact},${{_ELAPSED_MS}}" >> {HOME_DIR}/overhead_log.csv
"""

    script_name = f"job_{job_id:03d}.sh"

    with open(script_name, "w") as f:
        f.write(sbatch_content)

    try:
        result = subprocess.run(
            ["sbatch", script_name],
            capture_output=True, text=True, check=True
        )
        slurm_job_id = result.stdout.strip().split()[-1]
        will_timeout = t_req < t_fact  # теоретически (до округления SLURM)
        print(
            f"  Заявка {job_id:03d} | SlurmID: {slurm_job_id:>6} | "
            f"Лимит: {t_req:>4} с ({timelimit_str}) | "
            f"Факт: {t_fact:>4} с | "
            f"Узлов: {nodes} | "
            f"{'[TIMEOUT]' if will_timeout else ''}"
        )

        final_name = f"job_{job_id:03d}_slurm_{slurm_job_id}.sh"
        shutil.move(script_name, os.path.join(JOBS_DIR, final_name))
        return slurm_job_id

    except Exception as e:
        print(f"  Ошибка отправки заявки {job_id:03d} в SLURM: {e}")
        if os.path.exists(script_name):
            shutil.move(script_name, os.path.join(JOBS_DIR, f"job_{job_id:03d}_ERROR.sh"))
        return "ERROR"

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 simulator.py <количество_заявок>")
        print("  Количество заявок: целое число от 1 до 999")
        sys.exit(1)

    try:
        num_jobs = int(sys.argv[1])
        if not (1 <= num_jobs <= 999):
            raise ValueError
    except ValueError:
        print("Ошибка: количество заявок должно быть целым числом от 1 до 999.")
        sys.exit(1)

    if os.path.exists(JOBS_DIR):
        shutil.rmtree(JOBS_DIR)
    os.makedirs(JOBS_DIR, exist_ok=True)

    overhead_log = f"{HOME_DIR}/overhead_log.csv"
    if not os.path.exists(overhead_log):
        with open(overhead_log, "w") as f:
            f.write("SlurmJobID,SleepRequested_Sec,ActualElapsed_Ms\n")

    print(f"=== Имитатор заявок: запуск генерации {num_jobs} заявок ===")
    print(f"    Параметры модели: T_MIN={T_MIN} с, T_MAX={T_MAX} с, k={K_SCALE}")
    print(f"    μ={MU}, σ={SIGMA}, TIMEOUT_RATE={TIMEOUT_RATE}")
    print()

    with open(LOG_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Timestamp", "SimID", "SlurmJobID", "Nodes",
            "PlannedTime_Sec", "ActualTime_Sec", "Tau", "IsTimeout"
        ])

        for i in range(1, num_jobs + 1):
            t_fact, t_req, nodes, is_timeout = generate_job()
            tau = round(t_req / t_fact, 4)
            slurm_id = submit_to_slurm(i, t_fact, t_req, nodes)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                i, slurm_id, nodes,
                t_req, t_fact, tau, int(is_timeout)
            ])

    print()
    print(f"=== Генерация завершена. Статистика сохранена в {LOG_FILE} ===")
    print(f"    Сценарии задач сохранены в: {JOBS_DIR}")


if __name__ == "__main__":
    main()