#!/bin/bash

VMS=("master" "node1" "node2" "node3" "node4")

case "$1" in
    start)
        echo "=== Запуск виртуального кластера ==="
        for vm in "${VMS[@]}"; do
            echo "Запуск $vm..."
            # type headless запускает машины в фоновом режиме без открытия окон
            VBoxManage startvm "$vm" --type headless
        done
        echo "=== Все узлы отправлены на запуск ==="
        ;;
    stop)
        echo "=== Корректное выключение кластера ==="
        for vm in "${VMS[@]}"; do
            echo "Выключение $vm..."
            VBoxManage controlvm "$vm" acpipowerbutton
        done
        echo "=== Сигналы выключения отправлены ==="
        ;;
    status)
        echo "=== Статус виртуальных машин ==="
        VBoxManage list runningvms
        ;;
    *)
        echo "Использование: $0 {start|stop|status}"
        exit 1
        ;;
esac

# ssh vlad@127.0.0.1 -p 2222 подключение к вм
# cat /home/vlad/acct_0921-0923 | grep "|50430|" | grep "|run_bwa.sh|" > /home/vlad/my_variant_raw.txt
# cat /etc/hosts Проверка сети и разрешения имён (DNS/hosts)
# ping -c 2 node1
# ssh node1 "hostname; whoami" Проверка SSH с авторизацией по ключам
# id
# scontrol show nodes Просмотр настроек вычислительных узлов
# scontrol show partitions Просмотр настроек разделов (Partitions / Очередей)