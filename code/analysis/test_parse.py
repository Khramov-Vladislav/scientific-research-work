import os

RAW_FILE = "../data/my_variant_raw.txt"

if os.path.exists(RAW_FILE):
    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip(): # Берем первую непустую строку
                parts = line.strip().split('|')
                print(f"Всего колонок найдено: {len(parts)}\n")
                for index, value in enumerate(parts):
                    print(f"Слот [{index}]: {value}")
                break
else:
    print("Файл не найден")