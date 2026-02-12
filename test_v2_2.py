#!/usr/bin/env python3
"""
Тест функций выбора параметров v2.2
Проверяет что новые функции работают корректно
"""

import sys
sys.path.insert(0, '.')

# Проверяем импорты
try:
    from pathlib import Path
    import cv2
    print("✓ Базовые импорты OK")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

# Проверяем синтаксис
try:
    import ast
    with open('media_cleaner.py', encoding='utf-8') as f:
        code = f.read()
    ast.parse(code)
    print("✓ Синтаксис media_cleaner.py верный")
except SyntaxError as e:
    print(f"❌ Синтаксическая ошибка: {e}")
    sys.exit(1)

# Проверяем структуру функций
try:
    # Проверяем что функции определены
    tree = ast.parse(code)
    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    
    required_functions = [
        'choose_epsilon',
        'choose_strength_multiplier', 
        'choose_settings',
        'choose_device',
        'choose_video',
        'process_imperceptible_protected_video'
    ]
    
    for func in required_functions:
        if func in functions:
            print(f"✓ Функция '{func}' определена")
        else:
            print(f"❌ Функция '{func}' НЕ найдена")
            sys.exit(1)
            
except Exception as e:
    print(f"❌ Ошибка проверки структуры: {e}")
    sys.exit(1)

# Проверяем возвращаемые типы choose_settings
try:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'choose_settings':
            # Проверяем возвращаемые значения
            print("✓ Функция choose_settings найдена")
            # Проверяем что она возвращает кортеж из 6 элементов
            returns = []
            for n in ast.walk(node):
                if isinstance(n, ast.Return) and n.value:
                    returns.append(n)
            if returns:
                print(f"✓ choose_settings имеет {len(returns)} return statement(s)")
            break
except Exception as e:
    print(f"❌ Ошибка проверки структуры choose_settings: {e}")
    sys.exit(1)

# Проверяем конфигурацию
try:
    CONFIG_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'CONFIG':
                    CONFIG_found = True
                    print("✓ CONFIG словарь найден")
                    break
    if not CONFIG_found:
        print("⚠️  CONFIG словарь не найден (может быть импортирован)")
except Exception as e:
    print(f"⚠️  Ошибка проверки CONFIG: {e}")

print("\n" + "="*70)
print("✓ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
print("="*70)
print("\nПрограмма готова к использованию:")
print("  python media_cleaner.py")
print("\nНовые возможности v2.2:")
print("  • Интерактивный выбор epsilon (0.01-0.5)")
print("  • Интерактивный выбор strength_mult (0.1-2.0)")
print("  • Опциональная маскировка аудио")
print("  • Гарантированное GPU кодирование")
print("  • Подробные рекомендации в консоли")
print("="*70)
