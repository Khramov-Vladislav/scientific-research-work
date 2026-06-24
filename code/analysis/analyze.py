import math

# Читаем отфильтрованные строки
with open("./my_variant_raw.txt", "r") as f:
    lines = f.readlines()

elapsed_raw_list = []
tau_list = []

total_valid_jobs = 0
timeout_jobs_count = 0

for line in lines:
    parts = line.split('|')
    if len(parts) < 20:
        continue
        
    try:
        state = parts[9].strip()          # Индекс 9: State (Статус задачи)
        elapsed_raw = int(parts[17])      # Индекс 17: ElapsedRaw (сек)
        timelimit_raw = int(parts[18])    # Индекс 18: TimelimitRaw (мин)
        
        # 1. Игнорируем задачи, завершившиеся внутренней ошибкой программы
        if "FAILED" in state or "NODE_FAIL" in state or "CANCELLED" in state:
            continue
            
        # Отсекаем мгновенные сбои менее 10 сек
        if elapsed_raw > 10:
            total_valid_jobs += 1
            t_fact = elapsed_raw
            t_req = timelimit_raw * 60  # Переводим лимит в секунды
            
            # 2. Отдельно считаем и обрабатываем TIMEOUT задачи
            if "TIMEOUT" in state:
                timeout_jobs_count += 1
                # Не включаем их в расчет параметров распределения ошибок оценки,
                # так как их реальный t_fact оборван планировщиком.
                continue
            
            # Для успешно завершившихся (COMPLETED) считаем честный коэффициент Tau
            tau = t_req / t_fact
            elapsed_raw_list.append(t_fact)
            tau_list.append(tau)
            
    except ValueError:
        continue

if not elapsed_raw_list:
    print("Ошибка: Не найдено подходящих COMPLETED записей.")
else:
    t_min = min(elapsed_raw_list)
    t_max = max(elapsed_raw_list)

    log_taus = [math.log(t) for t in tau_list]
    n = len(log_taus)
    
    mu = sum(log_taus) / n
    variance = sum((x - mu) ** 2 for x in log_taus) / n
    sigma = math.sqrt(variance)
    
    # Доля таймаутов от общей массы успешных/таймаут задач
    timeout_rate = timeout_jobs_count / total_valid_jobs if total_valid_jobs > 0 else 0

    print(f"--- Результаты анализа ---")
    print(f"Минимум фактического времени (T_min): {t_min} сек")
    print(f"Максимум фактического времени (T_max): {t_max} сек")
    print(f"Параметр Mu (среднее ln(Tau)): {round(mu, 4)}")
    print(f"Параметр Sigma (отклонение ln(Tau)): {round(sigma, 4)}")
    print(f"Доля задач с ошибкой Timeout: {round(timeout_rate * 100, 2)}%")
