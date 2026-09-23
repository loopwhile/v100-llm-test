#!/usr/bin/env python3
"""One bounded, detached-safe llama.cpp C1 128K run for WBS 2.1.x.

Runs exactly one model/lane combination. Never retries, changes lanes, or
launches a follow-up experiment automatically.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import threading
import time

import bench_harness as h
import build_128k_workload as w
import runtime_launcher as launcher
from measurement_policy import future_config

ROOT = Path(__file__).resolve().parents[1]

MODEL_WBS = {
    'ornith-1.5-9b': '2.1.2',
    'ornith-1.5-35b-a3b': '2.1.3',
    'gemma4-26b-a4b': '2.1.4',
}


def command(args, timeout=30):
    return subprocess.run(
        args, capture_output=True, text=True, timeout=timeout, check=True
    ).stdout


def checkpoint(raw, phase, **extra):
    path = raw / 'runtime/progress.json'
    state = json.loads(path.read_text()) if path.exists() else {}
    h.save(path, state | dict(phase=phase, updated_at_utc=h.utc(), **extra))


def measure(raw):
    config = json.loads((raw / 'runtime/planned-config.json').read_text())
    adapter = h.HTTPAdapter(config['endpoint'], 'llama.cpp', timeout_s=1800)
    checkpoint(raw, 'running', step='materializing_live_tokenizer_workload')
    workload = w.build(
        w.load_manifest(ROOT / 'workloads/capacity/v1.json'),
        adapter,
        config['model'],
    )
    checkpoint(
        raw,
        'running',
        step='measured_request',
        workload_sha256=h.sha(h.canon(workload)),
    )
    verdict = h.run_batch(raw, config, workload, adapter)
    checkpoint(raw, 'results_saved', step='measurement_complete', verdict=verdict)


def run(args):
    if socket.gethostname().split('.')[0] != 'p520-llm':
        raise RuntimeError('requires p520-llm')
    lock_path = ROOT / 'results/experiment.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_locked(args)


def run_locked(args):
    wbs = MODEL_WBS[args.model]
    raw = ROOT / 'results/raw' / args.experiment_id
    raw.mkdir(parents=True, exist_ok=False)
    runtime = raw / 'runtime'
    runtime.mkdir()

    plan = launcher.build_plan(
        ROOT, args.model, args.lane, 1, 'tp2-shared', args.port
    )
    if not plan.get('supported_for_planning'):
        raise RuntimeError('unsupported plan: ' + plan.get('reason', 'unknown reason'))

    cmd = list(plan['commands'][0])
    name_index = cmd.index('--name') + 1
    cmd[name_index] = args.experiment_id.lower()
    cidfile = runtime / 'container.cid'
    cmd[2:2] = [
        '--cidfile',
        str(cidfile),
        '--label',
        'experiment=' + args.experiment_id,
    ]

    config = future_config(
        plan
        | dict(
            experiment_id=args.experiment_id,
            launch_command=shlex.join(cmd),
            backend_variant='stock',
            context_tokens=131072,
            context_test=True,
            min_context_utilization=.99,
            prefix_cache_lane='cold-independent',
            chat_template='embedded GGUF Jinja; enable_thinking=false',
            tool_parser='none',
            thinking=False,
            endpoint=plan['endpoints'][0],
            notes=(
                f'WBS {wbs}; one measured request; no full-size warmup; '
                '2048 output reserve, minimum 256.'
            ),
        )
    )
    if args.retry_of:
        config.update(
            retry_of=args.retry_of,
            retry_reason='harness_bug',
            retry_evidence=args.retry_evidence,
        )
        config = future_config(config)

    h.validate(config)
    h.save(runtime / 'plan.json', plan)
    h.save(runtime / 'planned-config.json', config)
    checkpoint(
        raw,
        'prepared',
        experiment_id=args.experiment_id,
        model=args.model,
        lane=args.lane,
        host=socket.gethostname(),
        remote_path=str(raw),
        started_at_utc=h.utc(),
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        pid=os.getpid(),
        process_start_ticks=Path('/proc/self/stat').read_text().split()[21],
        measurement_timeout_s=2400,
        startup_timeout_s=300,
        scope=f'WBS {wbs}: one C1 128K request for this model/lane',
        cleanup_policy='only cidfile container with matching experiment label',
        planned_config_sha256=h.sha(h.canon(config)),
        source_sha256={
            str(p.relative_to(ROOT)): h.sha(p.read_bytes())
            for p in sorted((ROOT / 'scripts').glob('*.py'))
        },
    )

    server = None
    stop = threading.Event()
    collector = None
    verdict = 'INCONCLUSIVE'
    error = None
    exit_code = 1

    def telemetry():
        with (runtime / 'gpu-telemetry.jsonl').open('x') as stream:
            while not stop.is_set():
                try:
                    value = command(
                        [
                            'nvidia-smi',
                            '--query-gpu=index,uuid,memory.used,power.draw,power.limit,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu',
                            '--format=csv,noheader,nounits',
                        ],
                        5,
                    )
                    stream.write(json.dumps(dict(at_utc=h.utc(), csv=value)) + '\n')
                    stream.flush()
                except Exception as exc:
                    stream.write(
                        json.dumps(dict(at_utc=h.utc(), error=str(exc))) + '\n'
                    )
                    stream.flush()
                stop.wait(2)

    try:
        inventory = command(['nvidia-smi']) + '\n' + command(['ss', '-ltnp'])
        (runtime / 'host-before.txt').write_text(inventory)
        if command(
            [
                'nvidia-smi',
                '--query-compute-apps=pid',
                '--format=csv,noheader',
            ]
        ).strip():
            raise RuntimeError('GPU has an existing compute process; refusing launch')

        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', args.port))

        check = launcher.preflight(plan)
        h.save(runtime / 'preflight.json', check)
        if not check['pass']:
            raise RuntimeError('runtime preflight failed')

        artifact = plan['model_identity']
        checksum = command(['sha256sum', artifact['path']], 300).split()[0]
        artifact_check = dict(
            path=artifact['path'],
            sha256=checksum,
            expected=artifact['sha256'],
        )
        if checksum != artifact['sha256']:
            raise RuntimeError('model SHA256 mismatch')
        if args.lane in ('MTP', 'MTP_NGRAM') and artifact.get('mtp_companion_required'):
            companion = artifact.get('mtp_companion') or {}
            companion_checksum = command(
                ['sha256sum', companion['path']], 300
            ).split()[0]
            artifact_check['mtp_companion'] = dict(
                path=companion['path'],
                sha256=companion_checksum,
                expected=companion['sha256'],
            )
            if companion_checksum != companion['sha256']:
                raise RuntimeError('MTP companion SHA256 mismatch')
        h.save(runtime / 'artifact-check.json', artifact_check)

        image = cmd[cmd.index('--entrypoint') + 2]
        (runtime / 'runtime-version.txt').write_text(
            command(
                [
                    'docker',
                    'run',
                    '--rm',
                    '--pull=never',
                    '--gpus',
                    'all',
                    '--entrypoint',
                    'llama-server',
                    image,
                    '--version',
                ],
                60,
            )
        )

        collector = threading.Thread(target=telemetry)
        collector.start()
        checkpoint(raw, 'running', step='server_startup')
        with (runtime / 'server-0.log').open('x') as log:
            server = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)

        adapter = h.HTTPAdapter(config['endpoint'], 'llama.cpp', timeout_s=5)
        deadline = time.monotonic() + 300
        while not adapter.health()['healthy']:
            if server.poll() is not None:
                log = (runtime / 'server-0.log').read_text(errors='replace').lower()
                verdict = (
                    'FAIL_OOM'
                    if any(
                        x in log
                        for x in ('out of memory', 'cuda error: out of memory')
                    )
                    else 'FAIL_STARTUP'
                )
                raise RuntimeError('server exited during startup')
            if time.monotonic() >= deadline:
                verdict = 'FAIL_TIMEOUT'
                raise TimeoutError('startup deadline expired')
            time.sleep(2)

        checkpoint(
            raw,
            'running',
            step='server_ready',
            container_id=cidfile.read_text().strip(),
        )
        with (runtime / 'measurement.log').open('x') as log:
            child = subprocess.run(
                [sys.executable, __file__, '--worker', str(raw)],
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=2400,
            )
        if child.returncode:
            raise RuntimeError('measurement worker failed; see measurement.log')

        verdict = json.loads((raw / 'completion.json').read_text())['verdict']
        exit_code = 0
    except subprocess.TimeoutExpired as exc:
        verdict = 'FAIL_TIMEOUT'
        error = str(exc)
    except Exception as exc:
        error = str(exc)
    finally:
        if not (raw / 'completion.json').exists():
            if not (raw / 'config.json').exists():
                h.save(raw / 'config.json', config)
                h.save(
                    raw / 'identity.json',
                    dict(
                        config_sha256=h.sha(h.canon(config)),
                        created_at_utc=h.utc(),
                    ),
                )
            h.save(
                raw / 'metrics.json',
                dict(verdict=verdict, c1_128k=False, error=error),
            )
            h.save(
                raw / 'completion.json',
                dict(
                    experiment_id=args.experiment_id,
                    verdict=verdict,
                    completed_at_utc=h.utc(),
                    error=error,
                ),
            )

        cleanup = {'container_stopped': False}
        if cidfile.exists():
            cid = cidfile.read_text().strip()
            try:
                info = json.loads(command(['docker', 'inspect', cid]))[0]
                if info['Config']['Labels'].get('experiment') != args.experiment_id:
                    raise RuntimeError('container ownership mismatch')
                h.save(runtime / 'container-inspect.json', info)
                command(['docker', 'stop', '--time', '10', cid], 30)
                cleanup['container_stopped'] = True
            except Exception as exc:
                cleanup['error'] = str(exc)

        if server:
            try:
                cleanup['server_exit_code'] = server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                cleanup['server_exit_pending'] = True

        stop.set()
        if collector:
            collector.join(timeout=10)

        h.save(runtime / 'cleanup.json', cleanup)
        (runtime / 'host-after.txt').write_text(command(['nvidia-smi']))
        checkpoint(
            raw,
            'results_saved',
            step='finished',
            verdict=verdict,
            error=error,
            exit_code=exit_code,
        )
        h.save(
            runtime / 'exit.json',
            dict(exit_code=exit_code, verdict=verdict, completed_at_utc=h.utc()),
        )
    return exit_code


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment-id')
    parser.add_argument('--retry-of')
    parser.add_argument('--retry-evidence')
    parser.add_argument('--model', choices=sorted(MODEL_WBS))
    parser.add_argument(
        '--lane',
        choices=['TARGET', 'NGRAM', 'MTP', 'MTP_NGRAM'],
    )
    parser.add_argument('--port', type=int, default=18080)
    parser.add_argument('--worker', type=Path)
    args = parser.parse_args()

    if args.worker:
        measure(args.worker)
    else:
        if args.retry_of and not args.retry_evidence:
            parser.error('--retry-of requires --retry-evidence')
        if not args.experiment_id or not args.model or not args.lane:
            parser.error('--experiment-id, --model, and --lane are required')
        if not __import__('re').fullmatch(
            r'EXP-V100-[A-Z0-9][A-Z0-9-]*', args.experiment_id
        ):
            parser.error('invalid experiment ID')
        raise SystemExit(run(args))
