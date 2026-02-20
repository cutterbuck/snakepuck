import os
import sys
import traceback

try:
    from app import create_app

    app = create_app()
    print("App created successfully", flush=True)
except Exception:
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8060))
    print(f"Starting on port {port}", flush=True)
    app.run(debug=False, host="0.0.0.0", port=port)
