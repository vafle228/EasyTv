# Эксперимент SeedVR2-3B FP8

Замер на RTX 5060 Ti 16 ГБ (Windows, Docker Desktop / WSL2), 13 ноября 2026 года. Исходник пользователя: 852×480, 23,976 кадра/с, длительность 40:52. Исходный файл, URL, веса, изображения и видео остаются локально в `D:\SeedVR2Benchmark`; в Git попадают только инструменты и результаты замера.

Это отдельный эксперимент. Адаптер RelayVSR, HTTP API, Compose и интерфейс EasyTv не изменены. `easytv-relayvsr-1` остановлен, вместо него для замера запущен `easytv-seedvr2`. Контейнер нового движка пока не обслуживает задания EasyTv.

## Среда

- [ComfyUI-SeedVR2_VideoUpscaler](https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler), commit `4490bd1f482e026674543386bb2a4d176da245b9` (v2.5.24), standalone CLI.
- DiT: `seedvr2_ema_3b_fp8_e4m3fn.safetensors`; SHA-256 `3bf1e43ebedd570e7e7a0b1b60d6a02e105978f505c8128a241cde99a8240cff`.
- VAE: `ema_vae_fp16.safetensors`; SHA-256 `20678548f420d98d26f11442d3528f8b8c94e57ee046ef93dbb7633da8612ca1`.
- PyTorch 2.10.0+cu128, SDPA, DiT хранится в FP8, вычисления и VAE используют BF16. FlashAttention, SageAttention и torch.compile не включались. Остальные версии: [environment.txt](environment.txt).
- Образ `easytv-seedvr2:benchmark` построен поверх уже установленного `easytv-relayvsr:latest`, чтобы повторно использовать CUDA/PyTorch. RelayVSR в новом контейнере не запускается. Полная воспроизводимость требует того же базового образа: тег `latest` сам по себе не фиксирует его содержимое.
- Контейнер: 16 ГиБ RAM, swap запрещён, 8 CPU, `/dev/shm` 1 ГиБ. Аллокатор PyTorch ограничен 85% VRAM. На компьютере 32 ГБ RAM; WSL доступно около 23,5 ГиБ.

## Методика

Из исходника получены FFV1-вырезки без потери качества: лицо с 03:00, детали/титры с 10:00, движение с 25:00. Предварительного уменьшения исходного разрешения нет. Для сравнения исходные кадры увеличиваются Lanczos до точного размера нейросетевого результата. Тестовые вырезки без звука.

`run_benchmark.py` запускает неизменённый upstream CLI в том же процессе. Полное время включает импорт библиотек, загрузку моделей, обработку, кодирование и завершение мониторинга. RAM процесса, память cgroup и общая занятость GPU опрашиваются примерно раз в 0,5 с; короткие пики могут быть пропущены. CUDA allocated/reserved снимаются отдельно, в том числе перед сбросами счётчиков upstream. Общая VRAM включает рабочий стол и другие GPU-процессы: перед тестами было занято около 1,2 ГиБ.

CLI получает видео частями по 24 кадра, обрабатывает пакетами по 5 или 9 кадров, переносит DiT/VAE на CPU между фазами и использует VAE tiling. Это замер коротких вырезок, а не доказательство постоянного потребления памяти на всей серии.

`analyze.py` проверяет фактически закодированные кадры через ffprobe и рассчитывает скорость по полному времени. Оценка времени всей серии — линейная экстраполяция коротких прогонов, включающих холодный запуск. Полная серия не обработана. Пилот на 9 кадрах служит проверкой запуска и не используется для оценки скорости длинного видео.

## Повторение

Сначала остановить прежний GPU-контейнер. Не запускать обе модели одновременно. Каталог `/benchmark` должен содержать `input`, `models`, `logs`, `output`; каталог `/experiment` — файлы этой папки. Веса скачать из официального репозитория модели, указанного в upstream README, и проверить SHA-256 выше.

```powershell
git clone https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler.git D:/SeedVR2Benchmark/vendor
git -C D:/SeedVR2Benchmark/vendor checkout 4490bd1f482e026674543386bb2a4d176da245b9
docker build -t easytv-seedvr2:benchmark -f experiments/seedvr2/Dockerfile D:/SeedVR2Benchmark/vendor
docker stop easytv-relayvsr-1
docker run -d --name easytv-seedvr2 --gpus all --memory 16g --memory-swap 16g --cpus 8 --shm-size 1g --mount type=bind,source=D:/SeedVR2Benchmark,target=/benchmark --mount "type=bind,source=$((Get-Location).Path)/experiments/seedvr2,target=/experiment,readonly" --env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True --env OMP_NUM_THREADS=4 --env HF_HUB_DISABLE_TELEMETRY=1 easytv-seedvr2:benchmark
```

Вырезка (путь к собственному видео подставить вместо `source.mp4`):

```powershell
docker exec easytv-seedvr2 ffmpeg -hide_banner -loglevel error -ss 600 -i /benchmark/input/source.mp4 -frames:v 96 -an -c:v ffv1 /benchmark/input/details-10m.mkv
```

Основной профиль 1080p:

```powershell
docker exec easytv-seedvr2 python /experiment/run_benchmark.py details1080_b9 /benchmark/input/details-10m.mkv --output /benchmark/output/details1080_b9.mp4 --model_dir /benchmark/models --resolution 1080 --max_resolution 1920 --batch_size 9 --load_cap 48 --chunk_size 24 --temporal_overlap 1 --uniform_batch_size --dit_offload_device cpu --vae_offload_device cpu --blocks_to_swap 0 --vae_encode_tiled --vae_decode_tiled --vae_encode_tile_size 640 --vae_decode_tile_size 640 --vae_encode_tile_overlap 64 --vae_decode_tile_overlap 64 --cache_dit --cache_vae --video_backend ffmpeg --color_correction lab --debug
```

Для первого прогона лица: 96 кадров, `batch_size=5`, tile 768. Для QHD: `resolution=1440`, `max_resolution=2560`, `batch_size=5`, tile 640. Точные аргументы сохраняются в `logs/<name>.summary.json`.

```powershell
docker exec easytv-seedvr2 python /experiment/compare.py /benchmark/input/details-10m.mkv /benchmark/output/details1080_b9.mp4 /benchmark/output/details-compare.png --frames 12
```

`analyze.py` ожидает `/benchmark/manifest.json` с полем `source.duration_s`, например `{"source":{"duration_s":2452.458667}}`. Не публиковать локальный manifest с пользовательской ссылкой.

## Результат и границы

Числа и выводы приведены в [results.md](results.md). Настройки профилей различаются, поэтому сравнение скорости между сценами не изолирует влияние размера пакета. Для проверки качества нет HR-эталона: резкость не доказывает достоверность новых деталей; PSNR/SSIM как доказательство улучшения не рассчитывались.

GPU-прогоны и ffprobe проверяют реальную модель и полученные файлы. Интеграция с API, передача на телевизор, звук, обработка всей серии и длительная стабильность памяти этим экспериментом не проверены.

## Сравнение с RelayVSR после уменьшения

Пользователь отдельно согласовал эксперимент с потерей части входных деталей: исходные фрагменты 852×480 уменьшаются Lanczos до 479×270, затем прежний RelayVSR делает ×4 до 1916×1080. Это позволяет сопоставлять кадры в одинаковом размере с SeedVR2. Это не новый профиль API и не скрытое изменение обычного апскейла.

`relay_benchmark.py` использует прежний `worker.inference.InferenceEngine` из `easytv-relayvsr:latest` (RelayVSR commit `e856773350f53036d825404c9ea9228e6dffadca`). Веса загружаются один раз. Первый прогон лица прогревает вычисления, второй прогон лица и остальные сцены используют уже загруженные модели. Между заданиями история кадров сбрасывается штатным worker. Имена результатов и этапы сохраняются в `relay.timings.json`; `analyze_relay.py` сопоставляет каждый интервал с телеметрией всей сессии.

Перед запуском RelayVSR закончить процесс SeedVR2 и остановить его контейнер. Для сравнения используется отдельный контейнер без HTTP-сервера и без доступа на запись к библиотеке EasyTv:

```powershell
docker stop easytv-seedvr2
docker run -d --name easytv-relayvsr-benchmark --gpus all --memory 16g --memory-swap 16g --cpus 8 --shm-size 1g --mount type=bind,source=D:/SeedVR2Benchmark,target=/benchmark --mount type=bind,source=D:/RelayVsrModel,target=/weights,readonly --mount "type=bind,source=$((Get-Location).Path)/experiments/seedvr2,target=/experiment,readonly" --env RELAYVSR_INPUT=/benchmark/input --env OMP_NUM_THREADS=4 --env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True easytv-relayvsr:latest sleep infinity
docker exec -e BENCHMARK_ENTRYPOINT=/experiment/relay_benchmark.py -e BENCHMARK_ENGINE=relayvsr easytv-relayvsr-benchmark python /experiment/run_benchmark.py relay_session
docker exec easytv-relayvsr-benchmark python /experiment/analyze_relay.py
```

Подготовка входа для каждой сцены (для лица 96 кадров, для деталей и движения 48):

```powershell
docker exec easytv-seedvr2 ffmpeg -hide_banner -loglevel error -i /benchmark/input/faces-03m.mkv -vf scale=479:270:flags=lanczos -pix_fmt bgr0 -c:v ffv1 -an /benchmark/input/faces270.mkv
```

Эту подготовку нужно выполнить до остановки SeedVR2 либо обычным локальным FFmpeg. Имена остальных входов — `details270.mkv`, `motion270.mkv`.

`viewer.html` можно скопировать как `index.html` в локальную папку с результатами. Он предлагает пары Lanczos/SeedVR2, Lanczos/RelayVSR и SeedVR2/RelayVSR. Для 1440p есть только SeedVR2. Публикация самих видео в репозитории не требуется.

## Проверка компиляции VAE

Для `torch.compile` дополнительно согласован и установлен g++ 14.2 внутри тестового контейнера. Системный Python и библиотеки приложения не менялись. В Dockerfile компилятор также указан для будущей сборки; первоначальный образ был собран до этого дополнения.

Повторный тест использует тот же фрагмент деталей и профиль batch 9 / tile 640, дополняя аргументы `--compile_vae --compile_mode default`. В окружении процесса: `TORCHINDUCTOR_COMPILE_THREADS=2`, `MAX_JOBS=2`, `TORCHINDUCTOR_CACHE_DIR=/benchmark/compile-cache`. Память контейнера ограничена как прежде. Время первой компиляции нужно отделять от скорости повторных частей. Кэш находится на Windows bind mount; это также часть условий данного измерения.
