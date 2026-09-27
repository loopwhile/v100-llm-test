# WBS 6.9 Combined Optimized CPU Serving Stack 실행 결과 보고서

## 1. 실행 개요

| 항목 | 내용 |
| :--- | :--- |
| **작업 항목** | WBS 6.9 (Combined optimized CPU serving stack — true-4K A/B/C/D) |
| **대상 모델** | Ornith 1.5 35B-A3B (`Ornith-1.5-35B-Q4_K_M.gguf`, KV `Q8_0`) |
| **실행 호스트** | `p520-llm` (`/home/loopwhile/v100-llm-test-wbs22-20260924`) |
| **최적화 스택 1 (OpenVINO)** | `p520-cpu-llama-opt:b10775` (`fb36832f7cd6`) — **CLOSED — FAIL / INCOMPATIBLE** |
| **최적화 스택 2 (OpenBLAS+LTO)** | `p520-cpu-llama-opt:b10775-blas` — **DONE (Prompt-TPS selection: Case D; TTFT: Case C)** |
| **하드웨어 정책** | GPU 클럭/전력/persistence mode 읽기 전용 유지, VRAM 0B 격리 |
| **자원 제약 (Coexistence)** | 4 physical CPU cores (`cpuset 1,2,3,4`), `-t 4 -tb 4`, memory mmap |

---

## 2. 1단계: OpenVINO 결합 스택 검증 및 장애 원인 분석

### 2.1 개요 및 빌드
- **이미지**: `p520-cpu-llama-opt:b10775` (OpenVINO 2026.3.1, OpenBLAS, LTO, `GGML_BACKEND_DL=ON`, `GGML_CPU_ALL_VARIANTS=ON`).
- **Preflight**: `results/raw/WBS69-OPT4K-PREFLIGHT.json` (OpenBLAS 및 OPENVINO0 디바이스 인식 통과).
- **장애 발생**: Case A (`EXP-P520-CPU-ORN15-35B-OPTSTACK-C1-4K-20260927-001`, `-b 1024 -ub 256`) 4K compile warmup 도중 `HTTP 500 / llama_decode ret = -3` 크래시.

### 2.2 심층 원인 (Root Cause)
1. **`ScatterBase` Rank Mismatch (`set_rows.cpp`)**:
   - Ornith 1.5 35B의 KV Cache 텐서(`cache_k_l3`)는 2D `[131072, 512]` 구조를 갖습니다.
   - llama.cpp의 `ggml-openvino` 변환기(`translate_set_rows`)는 대상 텐서를 4D로 고정 가정하고 4D updates 텐서를 생성하여 OpenVINO Core 검증(`scatter_base.cpp:52`)에서 `rank(data)=2, rank(indices)=1, rank(updates)=4` 위반 (`ov::Exception: Updates rank mismatch`).
2. **Recurrent/Conv State Dynamic Dimension 추론 불가**:
   - SSM/Conv 상태 노드(`conv_states_reshaped-0`, `state_predelta-0`)의 동적 차원 추론 실패로 정적 shape 고정 및 `incompatible input tensor` 예외 발생.
- **판정**: **`CLOSED — FAIL / INCOMPATIBLE`** (불변 증거 영구 보존).

---

## 3. 2단계: OpenBLAS + LTO True-4K 선별 (Cases A~D)

사용자 명시적 승인에 따라 크래시된 OpenVINO를 제외하고, 유효한 최적화 구성(OpenBLAS + LTO + Flash Attention + Prompt Cache)을 적용한 `p520-cpu-llama-opt:b10775-blas`로 4개 케이스 스크리닝을 진행했습니다.

### 3.1 실험 계약, 최종 matrix 및 사전 시도

- **최종 accepted matrix**: `005~008` 4개. 모두 정확히 **4,071 total prompt tokens**, 동일 prompt SHA256(`2378b3662af3...`), 동일 prefix SHA256(`01f0a0cb5cf8...`)를 사용했습니다.
- **Prefix cache**: 최종 prefix는 실측 1,623 tokens이며 네 케이스 모두 `cache_n >= 512` acceptance를 통과했습니다.
- **중요한 해석 제한**: total prompt는 같지만 cache reuse 양은 같지 않았습니다. llama.cpp timings의 실제 새 평가량은 `prompt_n = total prompt_tokens - cache_n`이므로 A~D의 measured prompt TPS를 순수 `b/ub` 차이로만 귀속할 수 없습니다.
- **CPU coexistence envelope**: `cpuset 1,2,3,4`, `-t 4 -tb 4`, `--n-gpu-layers 0`. WBS 6.9 runner에는 별도의 sampled GPU VRAM peak telemetry를 추가하지 않았으므로 이 보고서에서는 새로운 “VRAM 0B 실측”을 주장하지 않습니다.
- **pre-final attempts도 raw evidence로 보존**:
  - `...-OPTBLAS-...-001`: 이전 1,023-token prefix contract에서 measured request 완료(4,083 total prompt, cache_n 763, 19.63 tok/s). 최종 matrix와 prompt/prefix contract가 달라 superseded diagnostic입니다.
  - `...-OPTBLAS-...-002`: inference response 후 `cache_n=507 < 512` acceptance gate에서 실패했습니다.
  - 따라서 “4개 케이스” 또는 “4회”는 **최종 accepted comparison matrix 005~008**을 의미하며, WBS 6.9 과정에서 발생한 모든 물리 inference 실행 수를 의미하지 않습니다.

### 3.2 최종 accepted True-4K measured 결과

| Case | Experiment ID | `-b` | `-ub` | Total Prompt | Cache N | Evaluated `prompt_n` | Prompt Eval TPS | TTFT (s) | Decode TPS | Wall (s) |
|:---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | `...-005` | 1024 | 256 | 4,071 | 1,363 | 2,708 | 18.48 | 146.57 | 6.64 | 185.03 |
| B | `...-006` | 2048 | 512 | 4,071 | 1,107 | 2,964 | 21.62 | 137.11 | 5.41 | 184.30 |
| C | `...-007` | 4096 | 512 | 4,071 | 1,107 | 2,964 | 22.27 | **133.12** | 5.38 | 180.58 |
| D | `...-008` | 4096 | 1024 | 4,071 | 595 | 3,476 | **24.69** | 140.78 | 6.49 | **180.10** |

사전 정의된 selection metric인 Prompt Eval TPS 기준으로는 **Case D**가 winner이며 `WBS69-OPTBLAS-4K-WINNER.json`의 판정은 그대로 유효합니다. 다만 A~D의 cache_n과 prompt_n이 다르므로 A 18.48 → D 24.69의 **+33.6%는 순수 b/ub 개선율이 아니라 최종 cached-serving scenario에서 관찰된 prompt-eval TPS 차이**입니다.

실제 latency 관점에서는 **Case C의 TTFT 133.12s가 가장 짧고**, total wall은 C 180.58s / D 180.10s로 약 0.3% 차이라 사실상 비슷합니다. 따라서 D는 throughput-oriented, C는 TTFT-oriented 후보로 구분합니다.

### 3.3 동일 4K / cache_n=0 setup diagnostic

각 최종 케이스의 `setup-compile-warmup.json`에는 동일한 **4,086 prompt tokens / cache_n=0 / prompt_n=4,086** 요청이 저장되어 있습니다. 이는 setup request라 정식 measured matrix가 아니지만, cache reuse 차이가 없는 동일 조건에서 A~D `b/ub` 효과를 비교할 수 있는 보조 evidence입니다.

| Case | `-b/-ub` | Uncached 4K Prompt TPS |
|:---:|:---:|---:|
| A | 1024/256 | 19.91 |
| B | 2048/512 | 23.55 |
| C | 4096/512 | 23.74 |
| D | 4096/1024 | **26.02** |

- D는 A보다 약 **30.7%** 높은 prompt throughput을 보였습니다.
- B→C(`ub=512` 고정, `b=2048→4096`)는 약 **+0.8%**로 작았습니다.
- C→D(`b=4096` 고정, `ub=512→1024`)는 약 **+9.6%**였습니다.
- 따라서 현재 4K evidence에서는 단순 `b` 확대보다 **`ub` 확대의 영향이 더 뚜렷**합니다.

### 3.4 True-2K와 True-4K를 함께 본 결론

WBS 6.8 true-2K에서는 A 31.72 / B 31.32 / C 31.34 / D 30.64 tok/s로 A/B/C가 ±2% 동률이었고 큰 b/ub의 이점이 없었습니다. 반면 WBS 6.9의 동일 uncached 4K setup에서는 A 19.91 / B 23.55 / C 23.74 / D 26.02 tok/s로 큰 b/ub가 유리했습니다.

따라서 현재 증거가 지지하는 결론은 **CPU llama.cpp의 최적 b/ub가 prompt/context 길이에 따라 달라질 수 있다**는 것입니다. 2K 결과만으로 4K 이상 장문 prompt의 batch/ubatch 효과를 부정하지 않으며, 4K 결과를 32K의 절대 최적값으로도 일반화하지 않습니다.

---

## 4. 아티팩트 및 증거 목록

- **사전 검증**: [`results/raw/WBS69-OPTBLAS-4K-PREFLIGHT.json`](../results/raw/WBS69-OPTBLAS-4K-PREFLIGHT.json)
- **요약 보고서**: [`results/raw/WBS69-OPTBLAS-4K-SCREENING-SUMMARY.json`](../results/raw/WBS69-OPTBLAS-4K-SCREENING-SUMMARY.json)
- **위너 증거**: [`results/raw/WBS69-OPTBLAS-4K-WINNER.json`](../results/raw/WBS69-OPTBLAS-4K-WINNER.json)
- **케이스별 세부 디렉터리**:
  - Case A: [`results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-005/`](../results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-005/)
  - Case B: [`results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-006/`](../results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-006/)
  - Case C: [`results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-007/`](../results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-007/)
  - Case D: [`results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-008/`](../results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-008/)

---

## 5. 최종 종결

- **WBS 6 전체**: 6.1~6.8 (Dual-resident feasibility & True-2K) 및 6.9 (OpenBLAS True-4K) **완료 (DONE)**.
- **핵심 성능 결론**: 2K에서는 작은 b/ub가 충분했지만, 동일 uncached 4K diagnostic에서는 `4096/1024`가 가장 높은 prompt throughput을 보였다. 최적 b/ub는 context 길이에 의존하며, cached measured matrix에서는 D가 Prompt-TPS selection winner, C가 TTFT winner다.
- **다음 작업**: **WBS 5** (성능 최적화 및 모델별 최종 serving recipe 확정).
