from media_cleaner import check_gpu_encoder

print("\n" + "="*70)
print("Проверка доступности GPU кодеков")
print("="*70 + "\n")

encoder = check_gpu_encoder()

print(f"\n✓ Результат: используется кодек '{encoder}'")

if encoder == "libx264":
    print("⚠️  GPU кодеки недоступны (это нормально)")
else:
    print("✅ GPU кодеки доступны (видео будет кодироваться быстрее!)")

print("\n" + "="*70 + "\n")
