# Database Benchmark: PostgreSQL vs ClickHouse

Run a benchmark using Python to compare PostgreSQL and ClickHouse performance.

---

## Project Structure

Place the following files in your project directory before proceeding:

```
.
├── Dockerfile.clickhouse
├── Dockerfile.postgres
├── Dockerfile.sysbench
├── docker-compose.yml
└── scripts/
    └── data_gen.py
```

---

## Setup & Run

### 1. Start the Containers

Once all files are in place, build and start the services:

```bash
docker compose up -d --build
```

---

### 2. Verify Container Communication

Before running the benchmark script, confirm that the `sysbench` container can reach both databases.

**Login to the sysbench container:**

```bash
docker exec -it sysbench bash
```

**Test PostgreSQL connectivity:**

```bash
psql -U postgres -d postgres -h pg-sysbench
```

**Test ClickHouse connectivity:**

```bash
clickhouse-client --host ch-sysbench --port 9000
```

> If both connections succeed, the network is configured correctly and you're ready to proceed.

---

### 3. Run the Benchmark Script

From your **local machine** (outside the container), run:

```bash
python scripts/data_gen.py
```

---

## Output

Benchmark results are saved to:

```
benchmark_results_1.txt
```
