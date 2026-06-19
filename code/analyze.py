import math

# Читаем отфильтрованные строки
with open("./my_variant_raw.txt", "r") as f:
    lines = f.readlines()

elapsed_raw_list = []
tau_list = []

for line in lines:
    parts = line.split('|')
    if len(parts) < 20:
        continue
        
    try:
        elapsed_raw = int(parts[17])      # Индекс 17: ElapsedRaw (сек)
        timelimit_raw = int(parts[18])    # Индекс 18: TimelimitRaw (мин)
        
        # Отсекаем мгновенные сбои (задачи менее 10 сек) для чистой статистики
        if elapsed_raw > 10:
            t_fact = elapsed_raw
            t_req = timelimit_raw * 60  # переводим лимит из минут в секунды
            
            tau = t_req / t_fact
            elapsed_raw_list.append(t_fact)
            tau_list.append(tau)
    except ValueError:
        continue

if not elapsed_raw_list:
    print("Ошибка: Не найдено записей с фактическим временем выполнения > 10 секунд.")
else:
    # Метрики фактического времени
    t_min = min(elapsed_raw_list)
    t_max = max(elapsed_raw_list)

    # Логарифмы ошибок
    log_taus = [math.log(t) for t in tau_list]
    n = len(log_taus)
    
    # Вычисляем Mu (среднее арифметическое логарифмов)
    mu = sum(log_taus) / n
    
    # Вычисляем Sigma (стандартное отклонение логарифмов)
    variance = sum((x - mu) ** 2 for x in log_taus) / n
    sigma = math.sqrt(variance)

    print(f"--- Результаты анализа ---")
    print(f"Минимум фактического времени (T_min): {t_min} сек")
    print(f"Максимум фактического времени (T_max): {t_max} сек")
    print(f"Параметр Mu (среднее ln(Tau)): {round(mu, 4)}")
    print(f"Параметр Sigma (отклонение ln(Tau)): {round(sigma, 4)}")
