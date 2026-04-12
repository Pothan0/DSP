import os
import time
import subprocess
from pyngrok import ngrok

def deploy():
    # 1. Kill old processes
    print("🧹 Cleaning up old sessions...")
    if os.name == 'nt':
        os.system('taskkill /f /im ngrok.exe /t >nul 2>&1')
        os.system('taskkill /f /im python.exe /t >nul 2>&1')
    
    time.sleep(2)
    
    print("🚀 Starting SentriCore Security Gateway...")
    try:
        # Start Streamlit
        # We use 'python -m streamlit' to be safest
        subprocess.Popen(["python", "-m", "streamlit", "run", "app.py", "--server.port", "8501"])
        time.sleep(5)
        
        # Start Ngrok
        print("🔑 Authenticating...")
        ngrok.set_auth_token("3C1z0HygvZUo3Gabyc1WKExMm43_ZDD7PQ9W2mpZwqJnLccG")
        tunnel = ngrok.connect(8501)
        
        print("\n" + "="*60)
        print(f"🔥 DEPLOYMENT LIVE!")
        print(f"🔗 URL: {tunnel.public_url}")
        print("="*60 + "\n")
        print("Send the link to your sir. DO NOT CLOSE THIS WINDOW.")
        
        while True:
            time.sleep(10)
    except Exception as e:
        print(f"❌ Deploy error: {e}")

if __name__ == "__main__":
    deploy()
