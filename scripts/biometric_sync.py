import os
from zk import ZK, const
import psycopg2
try:
    from dotenv import load_dotenv
except ImportError:
    from dotenv.main import load_dotenv
from datetime import datetime

load_dotenv()

# Get sync-from date from environment
SYNC_FROM_DATE = os.getenv('SYNC_FROM_DATE')
if SYNC_FROM_DATE:
    SYNC_FROM_DATE = datetime.strptime(SYNC_FROM_DATE, '%Y-%m-%d')

# Database connection
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASS')
)
cur = conn.cursor()

def fetch_and_store(device_ip, device_serial, direction):
    zk = ZK(device_ip, port=4370, timeout=5)
    try:
        device = zk.connect()
        logs = device.get_attendance()
        for log in logs:
            user_id = log.user_id
            timestamp = log.timestamp
            # Only sync logs from SYNC_FROM_DATE onward if set
            if SYNC_FROM_DATE and timestamp < SYNC_FROM_DATE:
                continue
            # Insert into DB, ignore duplicates
            cur.execute("""
                INSERT INTO attendance_logs (user_id, device_serial, direction, timestamp)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, device_serial, timestamp) DO NOTHING
            """, (user_id, device_serial, direction, timestamp))
        conn.commit()
        device.disconnect()
    except Exception as e:
        print(f"Error with device {device_ip}: {e}")

# Fetch logs from both devices
fetch_and_store(os.getenv('IN_DEVICE_IP'), os.getenv('IN_DEVICE_SERIAL'), 'IN')
fetch_and_store(os.getenv('OUT_DEVICE_IP'), os.getenv('OUT_DEVICE_SERIAL'), 'OUT')

cur.close()
conn.close()