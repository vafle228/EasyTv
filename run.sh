#!/usr/bin/env bash
# EasyTv launcher.
#
#   ./run.sh            собрать и запустить в Docker (то же, что ./run.sh up)
#   ./run.sh down       остановить
#   ./run.sh logs       логи сервера
#   ./run.sh discover   показать телевизоры, которые видно с этого компьютера
#   ./run.sh rebuild    пересобрать без кэша (например, чтобы обновить yt-dlp)
#   ./run.sh test       прогнать тесты в Docker
#   ./run.sh native     запустить без Docker (нужны Python 3.11+ и Node.js)
set -euo pipefail
cd "$(dirname "$0")"

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

is_windows() { case "$(uname -s)" in MINGW* | MSYS* | CYGWIN*) return 0 ;; *) return 1 ;; esac; }

# IP of this computer in the home network (the address TVs will download videos from).
detect_host_ip() {
  local ip=""
  if is_windows; then
    ip=$(powershell.exe -NoProfile -Command \
      "\$r = Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Sort-Object { \$_.RouteMetric + \$_.InterfaceMetric } | Select-Object -First 1; (Get-NetIPAddress -InterfaceIndex \$r.ifIndex -AddressFamily IPv4).IPAddress" \
      2>/dev/null | tr -d '\r' | head -n1)
  elif [[ "$(uname -s)" == "Darwin" ]]; then
    ip=$(ipconfig getifaddr "$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')" 2>/dev/null || true)
  else
    ip=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "src") print $(i + 1)}' | head -n1 || true)
    [[ -n "$ip" ]] || ip=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
  fi
  echo "$ip"
}

# SSDP search from the host itself (multicast works here, unlike inside Docker).
# Prints description URLs of media renderers, one per line.
host_discover() {
  if is_windows; then
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$PWD/scripts/discover.ps1")" 2>/dev/null | tr -d '\r' | grep -E '^https?://' || true
  else
    local py
    py="$(command -v python3 || command -v python || true)"
    [[ -n "$py" ]] && "$py" scripts/discover.py 2>/dev/null | grep -E '^https?://' || true
  fi
}

load_config() {
  if [[ ! -f .env ]]; then
    cp .env.example .env
    info "Создал .env из .env.example (адреса телевизоров и прочие настройки лежат там)"
  fi
  set -a
  # shellcheck disable=SC1091
  source <(tr -d '\r' < .env)
  set +a

  EASYTV_PORT="${EASYTV_PORT:-8080}"
  EASYTV_NETWORK="${EASYTV_NETWORK:-bridge}"
  if [[ -z "${EASYTV_PUBLIC_HOST:-}" ]]; then
    EASYTV_PUBLIC_HOST="$(detect_host_ip)"
    [[ -n "$EASYTV_PUBLIC_HOST" ]] || die "Не смог определить IP компьютера в сети. Укажите EASYTV_PUBLIC_HOST в .env"
  fi
  if [[ -z "${EASYTV_SCAN_SUBNETS:-}" ]]; then
    EASYTV_SCAN_SUBNETS="${EASYTV_PUBLIC_HOST%.*}.0/24"
  elif [[ "$EASYTV_SCAN_SUBNETS" == "none" ]]; then
    EASYTV_SCAN_SUBNETS=""
  fi
  export EASYTV_PORT EASYTV_PUBLIC_HOST EASYTV_SCAN_SUBNETS EASYTV_NETWORK
}

discover_for_container() {
  EASYTV_TV_LOCATIONS=""
  if [[ "${EASYTV_HOST_DISCOVERY:-on}" == "off" ]]; then
    export EASYTV_TV_LOCATIONS
    return
  fi
  info "Ищу телевизоры с этого компьютера…"
  local found
  found="$(host_discover)"
  if [[ -n "$found" ]]; then
    while IFS= read -r url; do info "  нашёл: $url"; done <<< "$found"
    EASYTV_TV_LOCATIONS="$(paste -sd, - <<< "$found")"
  else
    warn "С компьютера телевизоры не видны. Сервер будет искать их по адресам из EASYTV_TV_HOSTS."
  fi
  export EASYTV_TV_LOCATIONS
}

compose() {
  local files=(-f docker-compose.yml)
  [[ "$EASYTV_NETWORK" == "host" ]] && files+=(-f docker-compose.host.yml)
  docker compose "${files[@]}" "$@"
}

open_browser() {
  local url="$1"
  if is_windows; then
    cmd.exe //c start "" "$url" >/dev/null 2>&1 || true
  elif [[ "$(uname -s)" == "Darwin" ]]; then
    open "$url" >/dev/null 2>&1 || true
  else
    xdg-open "$url" >/dev/null 2>&1 || true
  fi
}

wait_ready() {
  local url="http://localhost:${EASYTV_PORT}/api/tvs"
  for _ in $(seq 1 60); do
    if curl -fsS -o /dev/null "$url" 2>/dev/null; then return 0; fi
    sleep 1
  done
  return 1
}

require_docker() {
  command -v docker >/dev/null || die "Docker не найден. Установите Docker Desktop или запустите ./run.sh native"
  docker info >/dev/null 2>&1 || die "Docker не запущен. Откройте Docker Desktop и повторите."
}

print_summary() {
  info "Компьютер в сети: ${EASYTV_PUBLIC_HOST} (с этого адреса телевизоры забирают видео)"
  info "Адреса телевизоров: ${EASYTV_TV_HOSTS:-не заданы}${EASYTV_SCAN_SUBNETS:+; перебор подсети $EASYTV_SCAN_SUBNETS}"
  [[ "$EASYTV_NETWORK" == "host" ]] && info "Сеть контейнера: host"
  return 0
}

cmd_up() {
  require_docker
  load_config
  discover_for_container
  print_summary
  info "Собираю и запускаю контейнер…"
  compose up -d --build
  info "Жду, пока сервер поднимется…"
  if wait_ready; then
    local url="http://localhost:${EASYTV_PORT}"
    info "Готово: $url  (с телефона: http://${EASYTV_PUBLIC_HOST}:${EASYTV_PORT})"
    open_browser "$url"
  else
    warn "Сервер не ответил за минуту. Посмотрите логи: ./run.sh logs"
    exit 1
  fi
}

cmd_discover() {
  load_config
  info "Ищу телевизоры с этого компьютера (4 секунды)…"
  local found
  found="$(host_discover)"
  if [[ -z "$found" ]]; then
    warn "Ничего не нашлось. Проверьте, что телевизоры включены, а сеть в Windows частная."
    return 1
  fi
  echo "$found"
  info "Эти адреса можно вписать в EASYTV_TV_HOSTS в .env или в поле «Добавить по адресу» на сайте."
}

cmd_rebuild() {
  require_docker
  load_config
  compose build --no-cache --pull
  cmd_up
}

cmd_down() {
  require_docker
  load_config
  compose down
}

cmd_logs() {
  require_docker
  load_config
  compose logs -f --tail=200
}

cmd_test() {
  require_docker
  info "Собираю тестовый образ и запускаю тесты…"
  docker build --target test -t easytv:test .
  docker run --rm easytv:test
}

cmd_native() {
  load_config
  print_summary
  local py
  py="$(command -v python3 || command -v python || command -v py || true)"
  [[ -n "$py" ]] || die "Нужен Python 3.11+"
  command -v npm >/dev/null || die "Нужен Node.js (npm)"

  if [[ ! -d backend/.venv ]]; then
    info "Создаю виртуальное окружение Python…"
    "$py" -m venv backend/.venv
  fi
  local vpy="backend/.venv/bin/python"
  [[ -x "$vpy" ]] || vpy="backend/.venv/Scripts/python.exe"
  "$vpy" -m pip install -q --upgrade pip
  "$vpy" -m pip install -q -e backend

  info "Собираю фронтенд…"
  (cd frontend && npm install --no-audit --no-fund && npm run build)

  command -v ffmpeg >/dev/null || warn "ffmpeg не найден: ролики с YouTube будут в 360p. Поставьте ffmpeg для 1080p."

  export EASYTV_STATIC_DIR="$PWD/frontend/dist" EASYTV_DATA_DIR="$PWD/data"
  info "Запускаю на http://localhost:${EASYTV_PORT} (Ctrl+C — остановить)"
  (sleep 3 && open_browser "http://localhost:${EASYTV_PORT}") &
  exec "$vpy" -m easytv
}

case "${1:-up}" in
  up) cmd_up ;;
  down | stop) cmd_down ;;
  logs) cmd_logs ;;
  discover) cmd_discover ;;
  rebuild) cmd_rebuild ;;
  test) cmd_test ;;
  native) cmd_native ;;
  -h | --help | help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) die "Неизвестная команда: $1 (см. ./run.sh help)" ;;
esac
