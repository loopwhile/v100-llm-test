#!/usr/bin/env python3
"""Verify live tool calls and streaming against the deployed OpenAI API.

This sends small inference requests, including an assistant/tool round trip.
It does not execute returned tools or run a capacity/performance benchmark.
"""
import argparse
import datetime
import json
from pathlib import Path
import urllib.request


def call(base_url, payload):
    request = urllib.request.Request(
        base_url + "/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        if not payload.get("stream"):
            return json.load(response)
        content, calls, finish, reasoning_chars = [], {}, None, 0
        for line in response:
            if not line.startswith(b"data: "):
                continue
            raw = line[6:].strip()
            if raw == b"[DONE]":
                break
            event = json.loads(raw)
            if "error" in event:
                raise RuntimeError(event["error"])
            for choice in event.get("choices", []):
                delta = choice.get("delta", {})
                if delta.get("content"):
                    content.append(delta["content"])
                reasoning_chars += len(delta.get("reasoning") or delta.get("reasoning_content") or "")
                for tc in delta.get("tool_calls") or []:
                    target = calls.setdefault(tc["index"], {
                        "id": "", "type": "function", "function": {"name": "", "arguments": ""},
                    })
                    if tc.get("id"):
                        target["id"] = tc["id"]
                    for key in ("name", "arguments"):
                        target["function"][key] += (tc.get("function") or {}).get(key) or ""
                if choice.get("finish_reason"):
                    finish = choice["finish_reason"]
        return {"choices": [{"message": {
            "role": "assistant", "content": "".join(content),
            "tool_calls": [calls[k] for k in sorted(calls)],
        }, "finish_reason": finish}], "reasoning_chars": reasoning_chars}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    result = {"verified_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "base_url": base, "model": "Ornith-1.5-35B-A3B", "tests": []}
    expected = {"label": "docker-tool-probe", "count": 7, "active": True}
    tools = [{"type": "function", "function": {
        "name": "get_runtime_probe", "description": "Read a test value from the Docker runtime probe.",
        "parameters": {"type": "object", "properties": {
            "label": {"type": "string"}, "count": {"type": "integer"}, "active": {"type": "boolean"},
        }, "required": ["label", "count", "active"], "additionalProperties": False},
    }}]
    messages = [
        {"role": "system", "content": "Use the provided tool to retrieve the probe. Never invent its result. After a tool response, reply with only its probe_result value; do not call another tool."},
        {"role": "user", "content": "Call get_runtime_probe with these exact arguments: " + json.dumps(expected)},
    ]
    common = {"model": result["model"], "messages": messages, "tools": tools,
              "temperature": 0, "max_tokens": 512,
              "chat_template_kwargs": {"enable_thinking": False}}
    try:
        with urllib.request.urlopen(base + "/health", timeout=5) as response:
            assert response.status == 200
        last_message = None
        for name, choice, stream in [
            ("auto_nonstream", "auto", False), ("auto_stream", "auto", True),
            ("required_stream", "required", True),
            ("named_stream", {"type": "function", "function": {"name": "get_runtime_probe"}}, True),
        ]:
            response = call(base, {**common, "tool_choice": choice, "stream": stream})
            message = response["choices"][0]["message"]
            calls = message.get("tool_calls") or []
            assert len(calls) == 1, (name, response)
            assert calls[0]["id"], (name, response)
            assert calls[0]["function"]["name"] == "get_runtime_probe", (name, response)
            arguments = json.loads(calls[0]["function"]["arguments"])
            assert arguments == expected, (name, arguments)
            assert isinstance(arguments["count"], int) and not isinstance(arguments["count"], bool)
            assert isinstance(arguments["active"], bool)
            last_message = {"role": "assistant", "content": message.get("content"), "tool_calls": calls}
            result["tests"].append({"name": name, "status": "PASS", "arguments": arguments,
                                    "finish_reason": response["choices"][0]["finish_reason"]})
            print(name + ": PASS", flush=True)
        messages = messages + [last_message, {"role": "tool", "tool_call_id": last_message["tool_calls"][0]["id"],
                    "content": json.dumps({"probe_result": "DOCKER_TOOL_ROUNDTRIP_OK"})}]
        response = call(base, {**common, "messages": messages, "tool_choice": "auto", "stream": True})
        message = response["choices"][0]["message"]
        assert not message.get("tool_calls"), response
        assert "DOCKER_TOOL_ROUNDTRIP_OK" in message["content"], response
        result["tests"].append({"name": "tool_result_roundtrip_stream", "status": "PASS", "content": message["content"]})
        print("tool_result_roundtrip_stream: PASS", flush=True)
        with urllib.request.urlopen(base + "/health", timeout=5) as response:
            result["health_after_http"] = response.status
        assert result["health_after_http"] == 200
        result["status"] = "PASS"
    except Exception as error:
        result["status"] = "FAIL"
        result["error"] = str(error)
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
