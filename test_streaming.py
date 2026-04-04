"""Quick test to verify thinking events and streaming tokens."""
import requests, json

r = requests.post(
    "http://localhost:8000/api/chat",
    json={"messages": [{"role": "user", "content": "What is the duty cycle at 200A for MIG on 240V?"}]},
    timeout=120,
    stream=True,
)

text_count = 0
for line in r.iter_lines(decode_unicode=True):
    if line.startswith("data: "):
        evt = json.loads(line[6:])
        if evt["type"] == "thinking":
            print(f"  [THINKING] {evt['content']}")
        elif evt["type"] == "text":
            text_count += 1
            if text_count <= 5:
                print(f"  [TEXT token #{text_count}] {repr(evt['content'][:60])}")
        elif evt["type"] == "done":
            print(f"  [DONE] Total text tokens streamed: {text_count}")
            break

print("\nStreaming verified!" if text_count > 10 else "\nWARNING: Few tokens streamed")
