# Ornith 1.5 9B llama.cpp R1 운영

최종 [R1 레시피](../../reports/recipes/ornith9-llama-r1.md)의 GPU별 독립 서버 2개와
LiteLLM 단일 게이트웨이를 실행한다. 기존 35B 1Cat 연결의 18080 포트를 보존하기 위해
9B 백엔드는 P520의 19080/19081을 사용하며, OpenCode는 18079 게이트웨이로 연결한다.

## P520에서 실행

현재 상태(2026-10-03): 사용자 요청으로 게이트웨이와 백엔드 2개를 중지했다.
세 컨테이너 모두 `exited`, exit code 0이며, 이미지·설정·OpenCode 모델 등록은 보존했다.

배포 경로: `/home/loopwhile/ornith9-llama-r1`.

```bash
cd /home/loopwhile/ornith9-llama-r1
./serve.sh start
./serve.sh status
./serve.sh health
./serve.sh logs
./serve.sh logs backend-0
./serve.sh stop
```

컨테이너 이름은 `ornith9-llama-r1-backend-0`, `ornith9-llama-r1-backend-1`,
`ornith9-llama-r1-gateway`다. `unless-stopped`로 자동 시작하며 명시적으로 중지하면
다시 `start`할 때까지 중지 상태를 유지한다. 모델 로딩이 끝나야 health가 성공한다.

백엔드 이미지와 GGUF는 최종 레시피의 동일 artifact를 사용한다. LiteLLM 1.101.0도
설치되어 있던 이미지 digest로 고정한다. R1의 batch 512 / ubatch 256, GPU당 128K
컨텍스트·1 slot, FP16 KV, flash attention, target-only, `--jinja --reasoning off`를 유지한다.
운영 명령에는 모델 표시용 `--alias Ornith-1.5-9B`를 추가한다. 모델은 읽기 전용으로
마운트하며 GPU backend는 localhost 포트만 publish한다. 게이트웨이의 host network와
least-busy / backend당 max_parallel_requests=1 / num_retries=0은 측정 구성과 동일하다.

## 노트북 OpenCode

노트북에서 게이트웨이를 SSH로 전달한다.

```bash
ssh -N -T -o ExitOnForwardFailure=yes -L 127.0.0.1:18079:127.0.0.1:18079 p520
```

`~/.config/opencode/opencode.jsonc`의 `provider`에 아래 항목을 추가한다.

```json
{
  "ornith9-r1": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "Ornith 1.5 9B - llama.cpp R1",
    "options": {
      "baseURL": "http://127.0.0.1:18079/v1",
      "apiKey": "sk-no-key-required"
    },
    "models": {
      "Ornith-1.5-9B": {
        "name": "Ornith 1.5 9B - llama.cpp R1",
        "limit": {"context": 131072, "output": 4096}
      }
    }
  }
}
```

모델 선택 ID는 `ornith9-r1/Ornith-1.5-9B`다. OpenCode의 `/models`에서 선택하거나:

```bash
opencode --model ornith9-r1/Ornith-1.5-9B
```

기존 provider, 기본 model/small_model, permission 설정은 유지한다.
구성 방법은 [OpenCode provider 문서](https://opencode.ai/docs/providers/)를 따른다.
이번 운영 확인은 서버 시작 및 짧은 API/OpenCode 연동에 한정하며 128K/C2 성능 재측정이 아니다.

2026-10-03 서버 시작, API 도구 호출 5종 및 실제 OpenCode 읽기·쓰기 후 재읽기를 통과했다.
[배포 기록](../../state/ornith9-llama-r1-deployment.json)과
[검증 기록](../../state/ornith9-llama-r1-validation.json)을 참조한다.
