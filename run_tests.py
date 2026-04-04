"""Quick integration test for the OmniPro 220 Expert Agent."""
import requests
import json
import sys

BASE = "http://localhost:8000"

def test_health():
    print("=== HEALTH CHECK ===")
    r = requests.get(f"{BASE}/api/health")
    print(f"Status: {r.status_code}")
    h = r.json()
    print(f"Knowledge loaded: {h['knowledge_loaded']}")
    print(f"Chunks: {h['chunks_count']}, Images: {h['images_count']}")
    print(f"Model: {h['models']['chat_model']}")
    assert r.status_code == 200
    assert h["knowledge_loaded"] is True
    assert h["chunks_count"] > 0
    print("PASS\n")

def test_chat_duty_cycle():
    print("=== CHAT: Duty Cycle ===")
    r = requests.post(
        f"{BASE}/api/chat",
        json={"messages": [{"role": "user", "content": "What is the duty cycle at 200A for MIG welding?"}]},
        timeout=120,
    )
    print(f"Status: {r.status_code}")
    assert r.status_code == 200
    texts = []
    for line in r.text.strip().split("\n"):
        if line.startswith("data: "):
            try:
                d = json.loads(line[6:])
                if d.get("type") == "text":
                    texts.append(d["content"])
            except json.JSONDecodeError:
                pass
    full = " ".join(texts)
    print(f"Response preview: {full[:300]}...")
    assert len(full) > 50, "Response too short"
    print("PASS\n")

def test_chat_troubleshooting():
    print("=== CHAT: Troubleshooting ===")
    r = requests.post(
        f"{BASE}/api/chat",
        json={"messages": [{"role": "user", "content": "Wire keeps bird nesting, how do I fix it?"}]},
        timeout=120,
    )
    print(f"Status: {r.status_code}")
    assert r.status_code == 200
    texts = []
    for line in r.text.strip().split("\n"):
        if line.startswith("data: "):
            try:
                d = json.loads(line[6:])
                if d.get("type") == "text":
                    texts.append(d["content"])
            except json.JSONDecodeError:
                pass
    full = " ".join(texts)
    print(f"Response preview: {full[:300]}...")
    assert len(full) > 50, "Response too short"
    print("PASS\n")

def test_chat_polarity():
    print("=== CHAT: Polarity ===")
    r = requests.post(
        f"{BASE}/api/chat",
        json={"messages": [{"role": "user", "content": "What polarity do I use for TIG welding?"}]},
        timeout=120,
    )
    print(f"Status: {r.status_code}")
    assert r.status_code == 200
    texts = []
    for line in r.text.strip().split("\n"):
        if line.startswith("data: "):
            try:
                d = json.loads(line[6:])
                if d.get("type") == "text":
                    texts.append(d["content"])
            except json.JSONDecodeError:
                pass
    full = " ".join(texts)
    print(f"Response preview: {full[:300]}...")
    assert len(full) > 50, "Response too short"
    print("PASS\n")

def test_frontend():
    print("=== FRONTEND ===")
    r = requests.get(BASE)
    print(f"Status: {r.status_code}")
    assert r.status_code == 200
    assert "chat" in r.text.lower() or "OmniPro" in r.text
    has_voice = "SpeechRecognition" in r.text or "speechRecognition" in r.text
    print(f"Has voice feature: {has_voice}")
    assert has_voice, "Voice feature not found in frontend"
    print("PASS\n")

if __name__ == "__main__":
    passed = 0
    failed = 0
    tests = [test_health, test_frontend, test_chat_duty_cycle, test_chat_troubleshooting, test_chat_polarity]
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}\n")
            failed += 1
    
    print(f"{'='*40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED!")
