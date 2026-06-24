#!/bin/bash

# Количество заявок по умолчанию
JOBS_COUNT=${1:-30}

echo "=== Очистка старых очередей и логов ==="
scancel --user=vlad 2>/dev/null
rm -f /home/vlad/simulation_stats.csv
rm -f /home/vlad/slurm_real_fact.txt

echo "=== Проверка статуса кластера SLURM ==="
sinfo
echo "------------------------------------------------"

echo "=== Запуск имитатора пользовательских заявок ($JOBS_COUNT шт.) ==="
python3 /home/vlad/simulator.py $JOBS_COUNT

echo ""
echo "=== Мониторинг очереди задач и динамический сбор статистики ==="
echo "Задачи выполняются в масштабированном времени (sleep от 1 до 43 сек)."
echo "------------------------------------------------"

# Создаем заголовок для системного лога факта выполнения
echo "JobID|JobName|Nodes|State|ElapsedRaw" > /home/vlad/slurm_real_fact.txt

# Ассоциативный массив для отслеживания уже записанных в лог задач
declare -A PROCESSED_JOBS

# Собираем ID запущенных задач из сохраненного CSV симулятора
if [ -f /home/vlad/simulation_stats.csv ]; then
    JOB_IDS=($(tail -n +2 /home/vlad/simulation_stats.csv | cut -d',' -f3 | grep -v "ERROR"))
fi

# Если не удалось получить ID задач, завершаем работу
if [ ${#JOB_IDS[@]} -eq 0 ]; then
    echo "Ошибка: задачи не были запущены симулятором."
    exit 1
fi

# Цикл крутится, пока в очереди squeue у пользователя vlad есть хотя бы одна активная задача
while [ $(squeue -u vlad -h | wc -l) -gt 0 ]; do
    clear
    echo "=== Текущее состояние очередей кластера (squeue) ==="
    squeue -u vlad
    echo "------------------------------------------------"
    echo "Выполнение натурного эксперимента в SLURM. Мониторинг..."
    
    # Опрашиваем статус каждой задачи прямо во время их жизненного цикла
    for id in "${JOB_IDS[@]}"; do
        if [[ -z "${PROCESSED_JOBS[$id]}" ]]; then
            JOB_DATA=$(scontrol show job $id 2>/dev/null)
            if [ ! -z "$JOB_DATA" ]; then
                STATE=$(echo "$JOB_DATA" | grep -oP 'JobState=\K\S+')
                
                # Если задача перешла в любое финальное (терминальное) состояние
                if [[ "$STATE" == "COMPLETED" || "$STATE" == "TIMEOUT" || "$STATE" == "FAILED" || "$STATE" == "CANCELLED" ]]; then
                    NAME=$(echo "$JOB_DATA" | grep -oP 'JobName=\K\S+')
                    NODES=$(echo "$JOB_DATA" | grep -oP 'NumNodes=\K\d+')
                    
                    START_S=$(echo "$JOB_DATA" | grep -oP 'StartTime=\K\S+' | xargs -I {} date -d "{}" +%s 2>/dev/null)
                    END_S=$(echo "$JOB_DATA" | grep -oP 'EndTime=\K\S+' | xargs -I {} date -d "{}" +%s 2>/dev/null)

                    if [[ ! -z "$START_S" && ! -z "$END_S" && "$END_S" -gt "$START_S" ]]; then
                        ELAPSED=$((END_S - START_S))
                    else
                        ELAPSED=0
                    fi

                    # Записываем строго отформатированную строку факта
                    echo "$id|$NAME|$NODES|$STATE|$ELAPSED" >> /home/vlad/slurm_real_fact.txt
                    PROCESSED_JOBS[$id]=1
                fi
            fi
        fi
    done
    
    sleep 1
done

# Финальный проверочный проход «вдогонку» для сбора данных тех задач, которые завершились мгновенно
for id in "${JOB_IDS[@]}"; do
    if [[ -z "${PROCESSED_JOBS[$id]}" ]]; then
        JOB_DATA=$(scontrol show job $id 2>/dev/null)
        if [ ! -z "$JOB_DATA" ]; then
            STATE=$(echo "$JOB_DATA" | grep -oP 'JobState=\K\S+')
            NAME=$(echo "$JOB_DATA" | grep -oP 'JobName=\K\S+')
            NODES=$(echo "$JOB_DATA" | grep -oP 'NumNodes=\K\d+')
            
            START_S=$(echo "$JOB_DATA" | grep -oP 'StartTime=\K\S+' | xargs -I {} date -d "{}" +%s 2>/dev/null)
            END_S=$(echo "$JOB_DATA" | grep -oP 'EndTime=\K\S+' | xargs -I {} date -d "{}" +%s 2>/dev/null)
            
            [[ ! -z "$START_S" && ! -z "$END_S" && "$END_S" -gt "$START_S" ]] && ELAPSED=$((END_S - START_S)) || ELAPSED=0
            
            echo "$id|$NAME|$NODES|$STATE|$ELAPSED" >> /home/vlad/slurm_real_fact.txt
            PROCESSED_JOBS[$id]=1
        fi
    fi
done

LINES_TO_PRINT=$((JOBS_COUNT + 1))

echo "------------------------------------------------"
echo "Эксперимент успешно завершен!"
echo "1. Данные математического плана: /home/vlad/simulation_stats.csv"
echo "2. Системные логи реального кластера: /home/vlad/slurm_real_fact.txt"
echo "3. Сгенерированные .sh скрипты сохранены в: /home/vlad/saved_jobs/"
echo ""
echo "=== Вывод результатов из simulation_stats.csv ==="
head -n $LINES_TO_PRINT /home/vlad/simulation_stats.csv
echo ""
echo "=== Вывод результатов из slurm_real_fact.txt ==="
head -n $LINES_TO_PRINT /home/vlad/slurm_real_fact.txt