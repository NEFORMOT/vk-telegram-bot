
import os

# Список файлов бота
files = [
    'bot.py', 'image_analyzer.py', 'keywords.py', 'config.py', 'compliments.py'
]

total_lines = 0

for file in files:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            line_count = sum(1 for line in f if line.strip())  # Считаем только непустые строки
            total_lines += line_count
            print(f"{file}: {line_count} строк(и)")
    except Exception as e:
        print(f"Ошибка при обработке файла {file}: {e}")

print(f"Всего строк во всех файлах: {total_lines}")
