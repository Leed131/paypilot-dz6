import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
MODEL = "anthropic/claude-haiku-5.5"


def _completion(reply: dict, expectation_id: str) -> dict:
    if "tool_calls" in reply:
        message = {"role": "assistant", "content": None, "tool_calls": [
            {"id": tc["id"], "type": "function",
             "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}}
            for tc in reply["tool_calls"]]}
        finish = "tool_calls"
    else:
        message = {"role": "assistant", "content": reply["text"]}
        finish = "stop"
    return {"id": expectation_id, "object": "chat.completion", "model": MODEL,
            "choices": [{"index": 0, "finish_reason": finish, "message": message}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0}}


def _quoted(text: str, where: str) -> str:
    if "'" in text or "\\" in text:
        raise SystemExit(f"{where}: no apostrophes or backslashes in scripted text: {text!r}")
    return text


def _match_user(text: str) -> str:
    return f"$.messages[-1:][?(@.role == 'user' && @.content == '{text}')]"


def _match_tool_result(call_id: str) -> str:
    return f"$.messages[-1:][?(@.role == 'tool' && @.tool_call_id == '{call_id}')]"


def expectations_for(scenario: dict) -> list[dict]:
    out = []
    seen_users = set()
    for step, turn in enumerate(scenario["turns"], 1):
        where = f"{scenario['id']} step {step}"
        user = _quoted(turn["user"], where)
        if user in seen_users:
            raise SystemExit(f"{where}: user text repeats an earlier step: {user!r}")
        seen_users.add(user)
        if turn.get("live"):
            continue
        matcher = _match_user(user)
        for n, reply in enumerate(turn["model"], 1):
            expectation_id = f"{scenario['id'].lower()}-step{step}-reply{n}"
            out.append({
                "id": expectation_id,
                "httpRequest": {"method": "POST", "path": ".*/chat/completions",
                                "body": {"type": "JSON_PATH", "jsonPath": matcher}},
                "httpResponse": {"statusCode": 200,
                                 "headers": {"content-type": ["application/json"]},
                                 "body": _completion(reply, expectation_id)},
            })
            if "tool_calls" in reply:
                matcher = _match_tool_result(reply["tool_calls"][-1]["id"])
    return out


def main() -> None:
    scenarios = sorted((ROOT / "scenarios").glob("*.json"))
    expectations = []
    for path in scenarios:
        expectations += expectations_for(json.loads(path.read_text(encoding="utf-8")))
    target = ROOT / "mock" / "expectations.json"
    target.write_text(json.dumps(expectations, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(f"{len(expectations)} expectations from {len(scenarios)} scenarios -> {target.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
