#!/bin/bash
# run_experiment.sh — управляющий скрипт натурного эксперимента.
# Запускает имитатор заявок, отслеживает их выполнение в SLURM
# и собирает статистику «план – факт» для последующего анализа.
#
# Использование: bash run_experiment.sh [количество_заявок]
# По умолчанию: 716 заявок (≈ 0.5 × 1433 записей исходной выборки).

JOBS_COUNT=${1:-716}
HOME_DIR="/home/vlad"
STATS_CSV="${HOME_DIR}/simulation_stats.csv"
FACT_TXT="${HOME_DIR}/slurm_real_fact.txt"
OVERHEAD_CSV="${HOME_DIR}/overhead_log.csv"

echo "=== Подготовка эксперимента ==="
echo "    Количество заявок: ${JOBS_COUNT}"
echo "    Масштабирование: k=30 (диапазон 1–360 с, медиана ~30 с)"
echo ""

# Отменяем предыдущие задачи пользователя и очищаем логи
scancel --user=vlad 2>/dev/null
rm -f "${STATS_CSV}" "${FACT_TXT}" "${OVERHEAD_CSV}"

echo "=== Статус кластера SLURM перед запуском ==="
sinfo
echo "------------------------------------------------"

# Создаём заголовок лога накладных расходов заранее,
# чтобы задачи могли дозаписывать строки параллельно
echo "SlurmJobID,SleepRequested_Sec,ActualElapsed_Ms" > "${OVERHEAD_CSV}"

echo ""
echo "=== Запуск имитатора (${JOBS_COUNT} заявок) ==="
python3 "${HOME_DIR}/simulator.py" ${JOBS_COUNT}

if [ $? -ne 0 ]; then
    echo "Ошибка: имитатор завершился с ошибкой."
    exit 1
fi

# Считываем Slurm ID всех отправленных задач из CSV имитатора
if [ ! -f "${STATS_CSV}" ]; then
    echo "Ошибка: файл ${STATS_CSV} не создан."
    exit 1
fi

JOB_IDS=($(tail -n +2 "${STATS_CSV}" | cut -d',' -f3 | grep -v "ERROR"))

if [ ${#JOB_IDS[@]} -eq 0 ]; then
    echo "Ошибка: ни одна задача не была отправлена в SLURM."
    exit 1
fi

echo ""
echo "=== Мониторинг очереди (${#JOB_IDS[@]} задач) ==="
echo "    Задачи выполняются в масштабированном времени (1–360 с)."
echo "    Ожидайте завершения всех задач..."
echo "------------------------------------------------"

# Заголовок файла фактических данных планировщика
echo "JobID|JobName|Nodes|State|ElapsedRaw" > "${FACT_TXT}"

declare -A PROCESSED_JOBS

# Основной цикл мониторинга: крутится пока есть активные задачи
while [ $(squeue -u vlad -h | wc -l) -gt 0 ]; do
    clear
    echo "=== Очередь SLURM ($(date '+%H:%M:%S')) ==="
    squeue -u vlad
    echo "------------------------------------------------"

    for id in "${JOB_IDS[@]}"; do
        if [[ -z "${PROCESSED_JOBS[$id]}" ]]; then
            JOB_DATA=$(scontrol show job $id 2>/dev/null)
            if [ -z "$JOB_DATA" ]; then continue; fi

            STATE=$(echo "$JOB_DATA" | grep -oP 'JobState=\K\S+')

            if [[ "$STATE" == "COMPLETED" || "$STATE" == "TIMEOUT" || \
                  "$STATE" == "FAILED"    || "$STATE" == "CANCELLED" ]]; then

                NAME=$(echo  "$JOB_DATA" | grep -oP 'JobName=\K\S+')
                NODES=$(echo "$JOB_DATA" | grep -oP 'NumNodes=\K\d+')

                START_S=$(echo "$JOB_DATA" | grep -oP 'StartTime=\K\S+' \
                          | xargs -I {} date -d "{}" +%s 2>/dev/null)
                END_S=$(echo "$JOB_DATA"   | grep -oP 'EndTime=\K\S+'   \
                          | xargs -I {} date -d "{}" +%s 2>/dev/null)

                if [[ -n "$START_S" && -n "$END_S" && "$END_S" -gt "$START_S" ]]; then
                    ELAPSED=$((END_S - START_S))
                else
                    ELAPSED=0
                fi

                echo "$id|$NAME|$NODES|$STATE|$ELAPSED" >> "${FACT_TXT}"
                PROCESSED_JOBS[$id]=1
            fi
        fi
    done

    sleep 2
done

# Финальный проход: дозаписываем задачи, завершившиеся быстрее цикла
for id in "${JOB_IDS[@]}"; do
    if [[ -z "${PROCESSED_JOBS[$id]}" ]]; then
        JOB_DATA=$(scontrol show job $id 2>/dev/null)
        if [ -z "$JOB_DATA" ]; then
            # scontrol уже не помнит задачу — запрашиваем через sacct
            SACCT_LINE=$(sacct -j $id --noheader --format=JobID,JobName,NNodes,State,ElapsedRaw -P 2>/dev/null | head -1)
            if [ -n "$SACCT_LINE" ]; then
                SACCT_ID=$(echo    "$SACCT_LINE" | cut -d'|' -f1)
                SACCT_NAME=$(echo  "$SACCT_LINE" | cut -d'|' -f2)
                SACCT_NODES=$(echo "$SACCT_LINE" | cut -d'|' -f3)
                SACCT_STATE=$(echo "$SACCT_LINE" | cut -d'|' -f4)
                SACCT_ELAPS=$(echo "$SACCT_LINE" | cut -d'|' -f5)
                echo "$SACCT_ID|$SACCT_NAME|$SACCT_NODES|$SACCT_STATE|$SACCT_ELAPS" >> "${FACT_TXT}"
            fi
        else
            STATE=$(echo  "$JOB_DATA" | grep -oP 'JobState=\K\S+')
            NAME=$(echo   "$JOB_DATA" | grep -oP 'JobName=\K\S+')
            NODES=$(echo  "$JOB_DATA" | grep -oP 'NumNodes=\K\d+')
            START_S=$(echo "$JOB_DATA" | grep -oP 'StartTime=\K\S+' \
                      | xargs -I {} date -d "{}" +%s 2>/dev/null)
            END_S=$(echo   "$JOB_DATA" | grep -oP 'EndTime=\K\S+'   \
                      | xargs -I {} date -d "{}" +%s 2>/dev/null)
            [[ -n "$START_S" && -n "$END_S" && "$END_S" -gt "$START_S" ]] \
                && ELAPSED=$((END_S - START_S)) || ELAPSED=0
            echo "$id|$NAME|$NODES|$STATE|$ELAPSED" >> "${FACT_TXT}"
        fi
        PROCESSED_JOBS[$id]=1
    fi
done

echo ""
echo "================================================"
echo "  Эксперимент завершён."
echo "================================================"
echo ""
echo "Файлы результатов:"
echo "  1. План имитатора:          ${STATS_CSV}"
echo "  2. Факт планировщика:       ${FACT_TXT}"
echo "  3. Накладные расходы SLURM: ${OVERHEAD_CSV}"
echo "  4. Сценарии задач:          ${HOME_DIR}/saved_jobs/"
echo ""
echo "=== Первые 10 строк плана (simulation_stats.csv) ==="
head -11 "${STATS_CSV}"
echo ""
echo "=== Первые 10 строк факта (slurm_real_fact.txt) ==="
head -11 "${FACT_TXT}"
echo ""
echo "=== Накладные расходы: первые 10 измерений (overhead_log.csv) ==="
head -11 "${OVERHEAD_CSV}"