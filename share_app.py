from pyngrok import ngrok
import subprocess
import time
import os
import sys

def main():
    print("🚀 Starting SentriCore Public Tunnel...")
    
    # 1. Start Streamlit in the background
    # We use the current venv's streamlit
    # On Windows, it's venv\Scripts\streamlit
    streamlit_path = os.path.join("venv", "Scripts", "streamlit.exe")
    if not os.path.exists(streamlit_path):
        # Fallback to just "streamlit" if venv not found (unlikely here)
        streamlit_path = "streamlit"

    print(f"📦 Launching Streamlit dashboard...")
    # Use CREATE_NEW_CONSOLE to keep streamlit output separate if needed, 
    # or just subprocess.Popen
    process = subprocess.Popen([streamlit_path, "run", "app.py", "--server.port", "8501"])

    # 2. Start Ngrok Tunnel
    print("🔗 Opening Secure Tunnel via Ngrok...")
    try:
        # Open a HTTP tunnel on port 8501
        public_url = ngrok.connect(8501, "http")
        
        print("\n" + "="*50)
        print("✅ SENTRICORE IS LIVE")
        print(f"🌍 Public URL: {public_url.public_url}")
        print("="*50 + "\n")
        print("👉 Send this link to your sir for testing.")
        print("⚠️  Keep this terminal open! If you close it, the link will stop working.")
        
        # Keep the script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 Closing tunnel and stopping SentriCore...")
        ngrok.disconnect(public_url.public_url)
        process.terminate()

if __name__ == "__main__":
    main()
