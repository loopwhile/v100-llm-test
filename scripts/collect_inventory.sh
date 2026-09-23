#!/usr/bin/env bash
set -u -o pipefail

EXPECTED_HOST="${1:-p520-llm}"
ACTUAL_HOST="$(hostname -s 2>/dev/null || hostname)"

if [[ "${ACTUAL_HOST}" != "${EXPECTED_HOST}" ]]; then
  printf 'inventory refused: expected host %s, actual host %s\n' "${EXPECTED_HOST}" "${ACTUAL_HOST}" >&2
  exit 2
fi

section() {
  printf '\n===== %s =====\n' "$1"
}

run() {
  printf '\n$'
  printf ' %q' "$@"
  printf '\n'
  "$@" 2>&1
  local rc=$?
  if (( rc != 0 )); then
    printf '[unavailable/failed rc=%d]\n' "${rc}"
  fi
  return 0
}

run_sh() {
  local command="$1"
  printf '\n$ %s\n' "${command}"
  bash -lc "${command}" 2>&1
  local rc=$?
  if (( rc != 0 )); then
    printf '[unavailable/failed rc=%d]\n' "${rc}"
  fi
  return 0
}

read_file() {
  local path="$1"
  printf '\n$ cat %s\n' "${path}"
  if [[ -r "${path}" ]]; then
    cat "${path}"
  else
    printf '[unavailable: not readable]\n'
  fi
}

section "INVENTORY METADATA"
run date --iso-8601=seconds
run hostname
run hostnamectl
run uname -a
read_file /proc/sys/kernel/random/boot_id
read_file /etc/os-release

section "CPU"
run lscpu
run_sh 'command -v cpupower >/dev/null && cpupower frequency-info || true'
read_file /sys/devices/system/cpu/intel_pstate/no_turbo
read_file /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
read_file /sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq
read_file /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq

section "MEMORY"
run_sh 'find /sys/devices/system/edac/mc -maxdepth 4 -type f \( -name dimm_label -o -name size -o -name dimm_mem_type -o -name dimm_location \) -print -exec cat {} \;'
run_sh 'if command -v dmidecode >/dev/null; then sudo -n dmidecode --type 17 | sed -E "/Serial Number:|Asset Tag:/d"; else printf "dmidecode unavailable\n"; fi'
run free -h
run_sh 'command -v lsmem >/dev/null && lsmem || true'
read_file /proc/meminfo
run_sh 'command -v numactl >/dev/null && numactl --hardware || true'

section "GPU INVENTORY AND POLICY"
run nvidia-smi
run nvidia-smi -q -d CLOCK,POWER
run nvidia-smi -L
run nvidia-smi --query-gpu=index,uuid,name,driver_version,pstate,persistence_mode,power.limit,power.draw,clocks.sm,clocks.mem,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu --format=csv,noheader,nounits
run nvidia-smi topo -m
run_sh 'nvidia-smi nvlink -s 2>&1 || true'
run_sh 'nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory --format=csv,noheader,nounits 2>&1 || true'

section "PCIe"
run_sh 'command -v lspci >/dev/null && lspci -tv || true'
run_sh 'command -v lspci >/dev/null && lspci -nn | grep -iE "NVIDIA|3D controller|VGA compatible" || true'

section "POWER POLICY SERVICES — READ ONLY"
run systemctl is-active nvidia-v100-init.service
run systemctl is-active v100-clock-lock.service
run systemctl is-active cpu-power-tune.service
run_sh 'systemctl cat v100-clock-lock.service 2>&1 || true'
run_sh 'systemctl cat cpu-power-tune.service 2>&1 || true'

section "STORAGE"
run lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,MODEL
run df -hT

section "LISTENING PORTS"
run_sh 'command -v ss >/dev/null && ss -ltnp || true'

section "CONTAINERS"
run_sh 'command -v docker >/dev/null && docker ps --format "{{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}" || true'
run_sh 'command -v podman >/dev/null && podman ps --format "{{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}" || true'
run_sh 'ps -eo pid,ppid,user,comm | grep -iE "llama|vllm|python|docker|podman|PID" || true'

section "RUNTIME DISCOVERY — NO INFERENCE"
run_sh 'for cmd in git docker python3 llama-server llama-bench vllm; do printf "%-14s " "$cmd"; command -v "$cmd" || printf "not-found\n"; done'
run_sh 'git --version 2>&1 || true'
run_sh 'docker --version 2>&1 || true'
run_sh 'python3 --version 2>&1 || true'

section "NETWORK / HOST SUMMARY"
run ip -brief address
run ip route

section "DONE"
printf 'read-only inventory completed on %s\n' "${ACTUAL_HOST}"
