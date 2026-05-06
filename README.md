# Database Benchmark: PostgreSQL vs ClickHouse

Compare PostgreSQL and ClickHouse performance using two benchmark approaches.

---

## Project Structure

Place the following files in your project directory before proceeding:

```
.
├── Dockerfile.clickhouse
├── Dockerfile.postgres
├── Dockerfile.sysbench
├── Dockerfile.phoronix
├── docker-compose.yml
└── scripts/
    └── data_gen.py
```

---

## Setup

### Start the Containers

Once all files are in place, build and start the services:

```bash
docker compose up -d --build
```

---

### Verify Container Communication

Before running any benchmark, confirm that the `sysbench` container can reach both databases.

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

## Option 1 — Benchmark Using Python

Run the benchmark script from your **local machine** (outside the container):

```bash
python scripts/data_gen.py
```

**Output** is saved to:

```
benchmark_results_1.txt
```

---

## Option 2 — Benchmark Using Phoronix

Ensure `Dockerfile.phoronix` is available and confirm the PostgreSQL and ClickHouse containers are running before proceeding.

### 1. Build the Docker Image

```bash
docker build --no-cache -t phoronix-bench -f Dockerfile.phoronix .
```

### 2. Run the Container

```bash
docker run -it \
  --name phoronix-bench \
  --network benchmark_1_bench-net \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e DISPLAY=$DISPLAY \
  --privileged \
  phoronix-bench:latest bash
```

> If you were not dropped into the container shell automatically, attach with:
> ```bash
> docker exec -it phoronix-bench bash
> ```

---

### 3. PostgreSQL Client Setup

Install the PostgreSQL 16 client inside the container:

```bash
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo apt install postgresql-client-16
psql --version
```

---

### 4. ClickHouse Client Setup

Install the ClickHouse client inside the container:

```bash
# Install prerequisite packages
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg

# Download the ClickHouse GPG key and store it in the keyring
curl -fsSL 'https://packages.clickhouse.com/rpm/lts/repodata/repomd.xml.key' | \
  sudo gpg --dearmor -o /usr/share/keyrings/clickhouse-keyring.gpg

# Get the system architecture
ARCH=$(dpkg --print-architecture)

# Add the ClickHouse repository to apt sources
echo "deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg arch=${ARCH}] \
  https://packages.clickhouse.com/deb stable main" | \
  sudo tee /etc/apt/sources.list.d/clickhouse.list

# Update apt package lists and install
sudo apt-get update
sudo apt-get install -y clickhouse-client
```

---

### 5. Run the Benchmarks

#### ClickHouse Benchmark

```bash
clickhouse-benchmark \
  --host ch-sysbench \
  --port 9000 \
  --concurrency 16 \
  --timelimit 30 \
  --query "SELECT repo_name, count() AS stars FROM (SELECT number % 1000 AS repo_name FROM numbers(10000000)) WHERE repo_name IN (SELECT number % 2000 FROM numbers(500)) GROUP BY repo_name ORDER BY stars DESC LIMIT 10" \
  2>&1 | tee ch_join_benchmark_results.txt
```

| Flag | Description |
|------|-------------|
| `--concurrency` | Number of parallel clients (threads) running queries |
| `--timelimit` | Duration in seconds; queries run continuously for this period |

**Output** is saved to: `ch_join_benchmark_results.txt`

---

#### PostgreSQL Benchmark

Store your query in `pg_query_1.sql`, then run:

```bash
pgbench \
  -U postgres \
  -h pg-sysbench \
  -p 5432 \
  -c 16 \
  -j 16 \
  -T 30 \
  -n \
  -f pg_query_1.sql \
  postgres \
  2>&1 | tee pg_join_benchmark_results.txt
```

| Flag | Description |
|------|-------------|
| `-c` | Number of parallel clients running queries |
| `-j` | Number of CPU threads used |
| `-T` | Duration in seconds; queries run continuously for this period |
| `-n` | Skip vacuum before the run (no vacuuming) |
| `-f` | Path to the SQL file containing the query |

**Output** is saved to: `pg_join_benchmark_results.txt`
