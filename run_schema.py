import os
import oracledb

# Fetch configurations from environment variables
user = os.environ.get("ORACLE_USER")
password = os.environ.get("ORACLE_PASSWORD")

print("🔄 Reading schema.sql...")
try:
    with open("schema.sql", "r") as f:
        sql_commands = f.read().split(";")
except FileNotFoundError:
    print("❌ Error: schema.sql file not found!")
    exit(1)

print("🔄 Connecting directly to local Oracle instance...")
try:
    # Bypasses the network listener by using the local thick driver mode
    oracledb.init_oracle_client()
    
    # Connect directly to the local instance via SID
    connection = oracledb.connect(
        user=user,
        password=password,
        dsn="XE"
    )
    cursor = connection.cursor()
    
    print("🚀 Direct connection successful! Executing schema...")
    for command in sql_commands:
        cmd_clean = command.strip()
        if cmd_clean:
            cursor.execute(cmd_clean)
            
    connection.commit()
    print("\n✅ All Oracle tables created successfully!")
    
except Exception as err:
    print(f"\n❌ Error executing schema: {err}")
    print("💡 Tip: Double-check that your Oracle DB is running and credentials are correct.")
    
finally:
    if 'connection' in locals():
        cursor.close()
        connection.close()