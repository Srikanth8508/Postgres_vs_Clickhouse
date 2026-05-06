import time
import psycopg2
from clickhouse_driver import Client
import random

# Configuration
PG_CONFIG = {
    "host": "localhost",
    "database": "benchmark_db",
    "user": "bench",
    "password": "password",
    "port": 5432
}

CH_CONFIG = {
    "host": "localhost",
    "database": "test_db",
    "user": "bench",
    "password": "password",
    "port": 9000
}

def get_pg_conn():
    return psycopg2.connect(**PG_CONFIG)

def get_ch_client():
    return Client(
        host=CH_CONFIG['host'],
        port=CH_CONFIG['port'],
        user=CH_CONFIG['user'],
        password=CH_CONFIG['password'],
        database=CH_CONFIG['database']
    )

def benchmark():
    results = []

    # 1. Setup Connections
    try:
        pg_conn = get_pg_conn()
        pg_cur = pg_conn.cursor()
        ch_client = get_ch_client()
    except Exception as e:
        print(f"Failed to connect to databases: {e}")
        return

    # Define Schema
    setup_sql = """
    (id Int64, ts DateTime, cat String, val1 Float64, val2 Float64, val3 Float64,
     val4 Int64, val5 Int64, val6 Float64, val7 Float64)
    """

    # Create Tables
    print("Preparing tables...")
    pg_cur.execute(f"DROP TABLE IF EXISTS bench_data;")
    pg_cur.execute(f"CREATE TABLE bench_data {setup_sql.replace('Int64', 'BIGINT').replace('String', 'TEXT').replace('DateTime', 'TIMESTAMP').replace('Float64', 'DOUBLE PRECISION')};")

    ch_client.execute(f"DROP TABLE IF EXISTS bench_data;")
    ch_client.execute(f"CREATE TABLE bench_data {setup_sql} ENGINE = MergeTree() ORDER BY id;")
    pg_conn.commit()

    # Generate 100k rows
    print("Generating test data...")
    rows = 50000
    data = [(i, "2024-01-01 12:00:00", random.choice(['A','B','C','D']),
             random.random(), random.random(), random.random(),
             random.randint(0,1000), random.randint(0,1000),
             random.random(), random.random()) for i in range(rows)]

    def time_it(label, pg_func, ch_func):
        print(f"Running test: {label}...")
        # Postgres
        try:
            start = time.time()
            pg_func()
            pg_time = f"{(time.time() - start) * 1000:.0f}ms"
        except Exception as e:
            pg_time = "FAILED"

        # ClickHouse
        try:
            start = time.time()
            ch_func()
            ch_time = f"{(time.time() - start) * 1000:.0f}ms"
        except Exception as e:
            ch_time = "FAILED"

        results.append((label, pg_time, ch_time))

    # --- EXECUTE TESTS ---

    # 1. Bulk Insert
    time_it("Bulk Insert",
            lambda: pg_cur.executemany("INSERT INTO bench_data VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", data) or pg_conn.commit(),
            lambda: ch_client.execute("INSERT INTO bench_data VALUES", data))

    # 2. Single Insert
    def pg_single():
        for i in range(100):
            pg_cur.execute("INSERT INTO bench_data (id) VALUES (%s)", (999999+i,))
        pg_conn.commit()

    def ch_single():
        for i in range(100):
            ch_client.execute("INSERT INTO bench_data (id) VALUES", [(999999+i,)])

    time_it("Single Insert (100 rows)", pg_single, ch_single)

    # 3. Queries
    query_where = "SELECT * FROM bench_data WHERE cat = 'A' AND val4 > 500 LIMIT 1000"
    time_it("WHERE Condition", lambda: pg_cur.execute(query_where) or pg_cur.fetchall(), lambda: ch_client.execute(query_where))

    query_group = "SELECT cat, AVG(val1) FROM bench_data GROUP BY cat ORDER BY cat"
    time_it("Group+Order By", lambda: pg_cur.execute(query_group) or pg_cur.fetchall(), lambda: ch_client.execute(query_group))

    query_read = "SELECT * FROM bench_data"
    time_it("Read Table", lambda: pg_cur.execute(query_read) or pg_cur.fetchall(), lambda: ch_client.execute(query_read))

    query_like = "SELECT count(*) FROM bench_data WHERE cat LIKE 'A%'"
    time_it("Operators (LIKE)", lambda: pg_cur.execute(query_like) or pg_cur.fetchall(), lambda: ch_client.execute(query_like))

    query_join = "SELECT a.id, b.cat FROM bench_data a JOIN bench_data b ON a.id = b.id WHERE a.id < 5000"
    time_it("Joins", lambda: pg_cur.execute(query_join) or pg_cur.fetchall(), lambda: ch_client.execute(query_join))

    # --- OUTPUT GENERATION ---
    
    # 1. Print to console
    output_header = "\n" + "="*60 + "\n"
    output_header += f"{'Operation':<25} | {'PostgreSQL':<15} | {'ClickHouse':<15}\n"
    output_header += "-" * 60 + "\n"
    
    table_rows = ""
    for res in results:
        table_rows += f"{res[0]:<25} | {res[1]:<15} | {res[2]:<15}\n"
    
    output_footer = "="*60 + "\n"
    
    full_output = output_header + table_rows + output_footer
    print(full_output)

    # 2. Write to benchmark_results.txt
    with open("benchmark_results.txt", "w") as f:
        f.write(full_output)
    print("Results successfully saved to benchmark_results.txt")

if __name__ == "__main__":
    benchmark()
