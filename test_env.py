import sys
import os

print(f"Python Version: {sys.version}")
print(f"Current Directory: {os.getcwd()}")

modules = [
    "langchain",
    "langchain_community",
    "langchain_ollama",
    "presidio_analyzer",
    "presidio_anonymizer",
    "spacy",
    "sentence_transformers",
    "numpy",
    "sklearn",
    "fastapi",
    "uvicorn",
    "requests"
]

print("\n--- Module Import Check ---")
for mod in modules:
    try:
        __import__(mod)
        print(f"✅ {mod}: Installed")
    except ImportError as e:
        print(f"❌ {mod}: FAILED - {e}")

print("\n--- Model Check (Ollama) ---")
import subprocess
try:
    res = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if "llama3.2" in res.stdout:
        print("✅ llama3.2 (1B/3B): Found")
    else:
        print("❌ llama3.2: Missing")
except Exception as e:
    print(f"❌ ollama command failed: {e}")

print("\n--- Model Check (Spacy) ---")
try:
    import spacy
    if spacy.util.is_package("en_core_web_lg"):
        print("✅ en_core_web_lg: Found")
    else:
        print("❌ en_core_web_lg: Missing")
except Exception as e:
    print(f"❌ Spacy check failed: {e}")
