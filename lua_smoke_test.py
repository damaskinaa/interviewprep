import json
import time
import urllib.request

base = "http://127.0.0.1:8000"
session_id = "smoke-test-" + str(int(time.time()))

def post(path, payload, timeout=180):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.status, json.loads(res.read().decode())

def get(path, timeout=30):
    with urllib.request.urlopen(base + path, timeout=timeout) as res:
        return res.status, json.loads(res.read().decode())

checks = {}

status, health = get("/lua-health")
checks["health"] = status == 200 and health.get("status") == "ok"

status, mem = post("/lua-memory-add", {
    "session_id": session_id,
    "title": "Senior failure answer rule",
    "scope": "session",
    "content": "Strong failure answers require root cause analysis, permanent system change, measurable proof, and calm executive ownership."
})
checks["memory_add"] = status == 200 and mem.get("status") == "memory_added"

status, q = post("/lua-benchmark-question", {
    "session_id": session_id,
    "company": "Google",
    "role": "Program Manager",
    "question_number": 1,
    "focus_area": "failure ownership"
})
checks["benchmark"] = status == 200 and q.get("mode") == "benchmark_learning" and len(q.get("answer_options", [])) == 3

chosen = q["answer_options"][0]

status, selected = post("/lua-select-benchmark-answer", {
    "session_id": session_id,
    "user_choice": "A",
    "selected_answer": chosen
})
checks["chunks"] = status == 200 and selected.get("status") == "training_ready" and len(selected.get("memorisation_chunks", [])) == 5

status, listening = post("/lua-practice-benchmark-turn", {
    "session_id": session_id,
    "selected_answer": chosen,
    "spoken_attempt": "I am still thinking",
    "is_final": False
})
checks["listening"] = status == 200 and listening.get("status") == "saved_listening" and listening.get("should_respond") is False

for attempt in range(2):
    status, feedback = post("/lua-practice-benchmark-turn", {
        "session_id": session_id,
        "company": "Google",
        "role": "Program Manager",
        "focus_area": "failure ownership",
        "selected_answer": chosen,
        "spoken_attempt": "I missed a deadline and fixed it later.",
        "is_final": True
    })

checks["feedback"] = status == 200 and feedback.get("status") == "practice_feedback"
checks["mastery_attached"] = bool(feedback.get("mastery"))

status, mastery = get(f"/lua-mastery/{session_id}")
item = mastery.get("mastery", [{}])[0] if mastery.get("mastery") else {}
checks["mastery"] = status == 200 and mastery.get("count") == 1 and item.get("attempt_count") == 2

status, drill = post("/lua-retry-drill", {"session_id": session_id})
checks["drill"] = status == 200 and drill.get("status") == "drill_ready" and bool(drill.get("retry_script"))

status, escalation = post("/lua-escalation-challenge", {
    "company": "Google",
    "role": "Program Manager",
    "focus_area": "failure ownership",
    "previous_answer": "I missed a deadline and fixed it later.",
    "score": 8
})
checks["escalation"] = status == 200 and escalation.get("status") == "escalation_ready"

status, state = get(f"/lua-state/{session_id}")
checks["state"] = status == 200 and state.get("status") == "state_ready" and state.get("attempts") >= 2

print("SESSION:", session_id)
for name, ok in checks.items():
    print(f"{name}: {ok}")

print("FINAL PASS:", all(checks.values()))
