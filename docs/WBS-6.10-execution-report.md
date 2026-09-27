# WBS 6.10 Optimized CPU True-32K 실행 결과 보고서

## 1. 목적

WBS 6.9 true-4K에서 상위 후보였던 C(`b=4096, ub=512`)와 D(`b=4096, ub=1024`)가 true-32K에서도 실질적인 CPU prefill 성능 향상을 제공하는지 검증한다.

대상은 Ornith 1.5 35B-A3B Q4_K_M / Q8_0이며, CPU inference는 Xeon W-2135의 4 physical core를 사용했다.

## 2. 실행 스택

- runtime: llama.cpp b10775 / commit `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`
- image: `p520-cpu-llama-opt:b10775-blas`
- image digest: `sha256:5f4f7d9d7bc5c0539eef15d88c43051f23c3bc696acbbd7ab96da041eb29e3e9`
- OpenBLAS
- LTO
- `GGML_CPU_ALL_VARIANTS`
- Flash Attention ON
- weight repack
- `cpu-strict`
- `cpu-strict-batch`
- `poll=50`
- `poll-batch=1`
- mmap
- lazy-mode off
- server warmup
- ngram-mod 24/48/64
- prompt cache OFF
- GPU offload OFF
- server context 131,072
- CPU threads 4

`--prio 1` 및 `--prio-batch 1`은 요청되었으나 runtime에서 permission error가 발생하여 실제 priority 상승은 적용되지 않았다.

## 3. Initial attempt

`EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-001`

은 measured inference 전에 harness identity validation에서 종료됐다.

누락된 identity:

- `runtime_revision`
- `launch_command`
- `chat_template`
- `tool_parser`
- `thinking`

따라서 이 attempt는 measured request가 아니며 partial preparation evidence로만 보존한다.

runner 수정 후에는 immutable raw directory 생성 전에 `h.validate(config)`를 수행한다.

## 4. Corrected C32 결과

Experiment:

`EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-003`

Configuration:

- `b=4096`
- `ub=512`
- prompt cache OFF
- prompt tokens = 31,743
- raw prompt SHA256 = `75f3de663d9196805b399c70da3f1dd048629c9fca71b7337f0893b6b4527147`

Result:

| Metric | Result |
|---|---:|
| Verdict | PASS |
| Prompt tokens | 31,743 |
| Prefill TPS | 7.3849 tok/s |
| TTFT | 4,298.53 s |
| Decode TPS | 3.1405 tok/s |
| Batch wall | 4,553.92 s |
| Outer wall | 4,554.22 s |
| Peak VRAM GPU0 | 0 MiB |
| Peak VRAM GPU1 | 0 MiB |

TTFT는 약 71.64분, 전체 batch wall은 약 75.90분이다.

## 5. Long-context prefill behavior

llama.cpp runtime에서 동일 request의 누적 prefill throughput은 context가 증가할수록 지속적으로 감소했다.

| Processed tokens | Cumulative TPS |
|---:|---:|
| 4,096 | 23.32 |
| 8,192 | 18.39 |
| 12,288 | 14.61 |
| 16,384 | 12.05 |
| 20,480 | 10.28 |
| 24,576 | 8.99 |
| 28,672 | 7.99 |
| final | 약 7.39 |

따라서 WBS 6.9에서 관찰된 4K b/ub 효과를 32K 전체 prefill에 직접 일반화할 수 없다.

## 6. 기존 WBS 6.6 결과와 비교

기존 Ornith 32K observed result:

`EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260926-001`

| Metric | WBS 6.6 | WBS 6.10 C32 | Difference |
|---|---:|---:|---:|
| Prompt tokens | 31,743 | 31,743 | same |
| Prefill TPS | 7.6303 | 7.3849 | -3.22% |
| TTFT | 4,160.26 s | 4,298.53 s | +3.32% |
| Decode TPS | 3.1495 | 3.1405 | -0.28% |
| Batch wall | 4,443.18 s | 4,553.92 s | +2.49% |
| Peak VRAM | 0 MiB | 0 MiB | same |

두 실행은 동일 controlled A/B가 아니다.

WBS 6.6은 native CPU serving stack 및 dual-resident 실행이었고, WBS 6.10은 OpenBLAS/LTO/repack/FA 등을 포함한 combined optimized stack과 single-server 실행이다.

따라서 성능 차이를 특정 단일 최적화의 효과로 귀속하지 않는다.

직접 확인된 사실은 **현재 combined optimized C32 configuration이 기존 32K observed result를 상회하지 못했다**는 것이다.

## 7. D32 미실행

계획된 D32:

`EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-004`

는 실행하지 않았다.

C32 한 건이 약 76분의 wall time을 소모했지만 기존 32K observed result보다 높은 성능을 보이지 못했다. 프로젝트 목적이 32K 실질 성능 향상이었기 때문에 추가 장시간 D32 실행의 기대 가치가 낮다고 판단했고, 사용자가 C32 result 저장 직후 runner를 종료했다.

따라서:

- C32: PASS
- D32: NOT RUN — INTENTIONALLY STOPPED
- C-vs-D complete comparison: NOT COMPLETED
- aggregate `WBS610-OPTBLAS-32K-C-VS-D.json`: 생성되지 않음

D32가 실행되지 않았으므로 `ub=1024`가 true-32K에서 C32보다 빠른지 여부는 판정하지 않는다.

## 8. Evidence

- `results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-001/`
- `results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-003/`
- `results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-003/wbs610-result.json`
- `results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-003/metrics.json`
- `results/raw/EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-003/runtime/server.log`

## 9. Final verdict

**WBS 6.10: CLOSED — C32 PASS / C32 DID NOT OUTPERFORM PRIOR 32K OBSERVATION / D32 NOT RUN**

이 결과는 개별 최적화가 각각 무효임을 증명하는 것이 아니다.

증명된 범위는 **현재 combined optimized C32 serving configuration이 기존 Ornith 32K observed result보다 빠르지 않았다**는 것이다. D32는 실행하지 않았으므로 optimized stack 전체 또는 `ub=1024`의 32K 성능까지 부정하는 결론으로 확대하지 않는다.
