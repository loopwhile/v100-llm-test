# WBS 1.1 — Host Snapshot

## Verdict

PASS

## Target

- Host: p520-llm
- OS: Ubuntu 26.04.1 LTS
- Kernel: 7.0.0-31-generic
- CPU: Intel Xeon W-2135, 6C/12T
- RAM: 61 GiB

## NVIDIA

- Driver: 580.178.04
- Driver CUDA compatibility: 13.0
- GPU0: Tesla V100-SXM2-16GB, 16384 MiB
- GPU1: Tesla V100-SXM2-16GB, 16384 MiB
- Persistence mode: Enabled on both GPUs
- Power limit: 150 W per GPU
- Power limit range: 150–300 W
- Default power limit: 300 W
- Idle graphics/SM clock: 135 MHz
- Memory clock: 877 MHz
- GPU utilization at snapshot: 0%
- GPU compute processes: none
- Volatile uncorrectable ECC errors shown by nvidia-smi: 0

## Runtime environment

- Running Docker containers: none
- Active LLM/API server: none
- Benchmark ports 18079/18080/18081: free
- Existing monitoring/listening services do not conflict with benchmark ports.

## Notes

- Hardware policy was observed only. No power, clock, persistence, driver, kernel, or CPU policy was changed.
- The `/dev/nvidia*` user shown in the snapshot was the `nvidia-smi` process used to collect the snapshot itself.
- The `pgrep` result containing the snapshot shell was a self-match caused by the search expression embedded in the command line.
- Runtime stdout/stderr preservation will be verified when the pinned runtimes are actually started in WBS 1.2/1.3.

## Evidence

- `host-snapshot.txt`
