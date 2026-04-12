import time
from pyngrok import ngrok

def start_tunnel():
    print("🚀 Initializing SentriCore Public Tunnel...")
    try:
        # Connect to port 8501
        tunnel = ngrok.connect(8501)
        print("\n" + "!" * 50)
        print(f"✅ DEPLOYED! Testing URL: {tunnel.public_url}")
        print("!" * 50 + "\n")
        print("👉 Tell your sir he can access it now.")
        print("⚠️  WE ARE IN LIVE MODE. DO NOT CLOSE THIS SESSION.")
        
        # Keep the process alive
        while True:
            time.sleep(10)
    except Exception as e:
        print(f"❌ Tunnel Failed: {e}")

if __name__ == "__main__":
    start_tunnel()
