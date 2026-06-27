import re, pathlib
p = pathlib.Path("rag/clients.py")
src = p.read_text(encoding="utf-8")

new_fn = '''def llm_generate(prompt: str, system: str = "", temperature: float = 0.1) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    r = requests.post(f"{OLLAMA_URL}/api/chat", json={
        "model": LLM_MODEL, "messages": messages,
        "stream": False, "options": {"temperature": temperature, "num_predict": 512},
    }, timeout=300)
    r.raise_for_status()
    return r.json().get("message", {}).get("content", "").strip()
'''

pattern = re.compile(r"def llm_generate\(.*?return r\.json\(\)\.get\(\"response\", \"\"\)\.strip\(\)\n", re.S)
src2, n = pattern.subn(new_fn, src)
p.write_text(src2, encoding="utf-8")
print("Patched llm_generate:", n, "replacement(s)")
