import time
from farm import clock

if __name__ == "__main__":
    print("[clock_worker] Starting background clock worker. Checking for seeds every 3 seconds...")
    while True:
        clock()
        time.sleep(3) 
