"""
Main run script for the Nasdaq Navigator

Usage:
    "python main_backend.py" when in the tradingadviceweb2 directory
"""

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading


    def open_browser():
        import time
        time.sleep(1.5)  # Wait for server start
        webbrowser.open("http://127.0.0.1:8000")


    print("Starting Trading Advice Web Application...")
    print("Server will be available at: http://127.0.0.1:8000")
    print("Browser will open automatically...")

    # Start browser opening in diff thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Run the uvicorn server
    uvicorn.run(
        "backend.main_backend:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )