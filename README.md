
Agent Catalog & Usage Examples
------------------------------

Here are the specific usage instructions for the agents available in this repository.

### Cross-Border Finance Agent (`cross-border-finance`)

A comprehensive agent for cross-border financial tasks, including exchange rate locking, compliance checks, and tax reporting.

- **Exchange Rate Lock Engine (UI)**
  Launch the Streamlit UI to analyze exchange rates and get lock recommendations.
  ```bash
  make exec AGENT=cross-border-finance ARGS="ui"
  ```

- **Compliance Self-Check Tool (UI)**
  Launch the Streamlit UI to upload transaction CSVs and generate compliance reports (PDF/Excel).
  ```bash
  make exec AGENT=cross-border-finance ARGS="compliance"
  ```

- **ATO Tax Report Tool (UI)**
  Launch the Streamlit UI to generate ATO-compliant tax declaration PDFs from transaction data.
  ```bash
  make exec AGENT=cross-border-finance ARGS="tax-report"
  ```

- **Blockchain Log Evidence Module (UI)**
  Launch the Streamlit UI to hash logs and upload evidence to Sepolia testnet.
  ```bash
  make exec AGENT=cross-border-finance ARGS="blockchain-log"
  ```

### Model Verify Agent (`model-verify`)

A utility agent to verify model access and API keys.

- **Verify Model Access**
  ```bash
  # Check if OPENAI_API_KEY works for gpt-3.5-turbo
  make exec AGENT=model-verify ARGS="--key-name OPENAI_API_KEY --model gpt-3.5-turbo"

  # Check with a custom base URL (e.g., for local models or other providers)
  make exec AGENT=model-verify ARGS="--key-name OPENAI_API_KEY --model gpt-3.5-turbo --base-url https://api.openai.com/v1"
  ```

### Tavily Search Agent (`tavily-search`)

An agent that performs web searches using the Tavily API.

- **Perform a Search**
  ```bash
  # Basic search
  make exec AGENT=tavily-search ARGS="search 'latest financial news in Australia'"

  # Search with topic and depth
  make exec AGENT=tavily-search ARGS="search 'RBA interest rate' --topic finance --search-depth advanced"
  ```

### DeepQuant Agent (`deepquant`)

An agent wrapping the DeepQuant backtesting engine.

- **Run Backtest**
  ```bash
  make exec AGENT=deepquant ARGS="Backtest AAPL from 2023-01-01 to 2023-12-31 with 10000 usd and sma 20 and sma 50"
  ```

### User Management Framework (`framework`)

The project includes a reusable Flask-based user management framework located in `src/framework`.

#### Database Migrations
We use `flask-migrate` (Alembic) to manage database schema changes.

**1. Setup Environment**
Ensure your `.env` file has the correct `DATABASE_URL`. If not set, it defaults to a local SQLite `finagent.db`.

**2. Initialize Migrations (First time only)**
```bash
export FLASK_APP=src/run_server.py
flask db init
```

**3. Generate Migration Script**
Run this whenever you modify `src/framework/models.py`:
```bash
export FLASK_APP=src/run_server.py
flask db migrate -m "Describe your changes"
```

**4. Apply Migrations**
Apply the changes to the database:
```bash
export FLASK_APP=src/run_server.py
flask db upgrade
```

**5. Quick Start (Development)**
To initialize the database without migrations (for quick testing):
```bash
python src/framework/init_db.py
```
