# Portfolio Visualization Project

This project consists of three main components that work together to visualize the performance of a trading strategy against a market benchmark.

1.  **Data Retrieval (Python):** The `driver.py` script (which utilizes `data_collection.py`) fetches historical stock data from Yahoo Finance and saves it to a `collected_data` directory.

2.  **Strategy Execution (Go):** The `algorithm.go` program processes the stock data and executes a trading strategy, logging the results to a `trade_ledger.txt` file.

3.  **Visualization (Python):** The `visualizations.py` script reads the trade ledger, calculates the cumulative portfolio value, and generates an interactive HTML chart comparing your strategy's performance to the S&P 500 (SPY).

### Prerequisites

To run this entire project on a Mac, you'll need the following installed:

* **Python 3.x**

* **pip** (Python's package installer)

* **Go environment** (version 1.16 or higher is recommended)

### Setup

Follow these steps to set up your environment and install all the required dependencies.

1.  **Go Program Setup:**
    First, set up your Go project and install any dependencies for `algorithm.go`. Navigate to your project directory in the terminal and run:

    ```bash
    go mod init <your-module-name>
    go tidy
    ```

2.  **Python Environment Setup:**
    It's a best practice to use a virtual environment to manage your Python dependencies. Open your terminal and run:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Python Dependencies:**
    With the virtual environment activated, install the necessary libraries for both data retrieval and visualization using `pip`:

    ```bash
    pip install pandas plotly kaleido yfinance
    ```

### Usage

Follow these steps in order to run the full workflow.

1.  **Step 1: Data Retrieval**
    Run the `driver.py` script from your terminal to download the necessary stock data.

    ```bash
    python3 driver.py
    ```

    This script will create a `collected_data` directory (if it doesn't already exist) and save the required `.csv` files inside.

2.  **Step 2: Strategy Execution**
    Next, run your Go program to generate the `trade_ledger.txt` file.

    ```bash
    go run algorithm.go
    ```

    The script assumes this file will be saved either in the same directory as the Python scripts or in the `collected_data` sub-directory.

3.  **Step 3: Visualization**
    Finally, run the visualization script to generate the final chart.

    ```bash
    python3 visualizations.py
    ```

### Workflow Options

Alternatively, ou can use the `run_workflow.sh` script to execute different parts of the workflow. The script provides the following options when in the `/src` directory:

- **Run the data collection script**:
  ```bash
  ./run_workflow.sh -d
  ```

- **Run the Go program**:
  ```bash
  ./run_workflow.sh -g
  ```

- **Run the visualization script**:
  ```bash
  ./run_workflow.sh -v
  ```

- **Run the Go program and visualization script together**:
  This is the most common workflow after the data collection step has already been completed.
  ```bash
  ./run_workflow.sh -gv
  ```

- **Run all steps (data collection, Go program, and visualization)**:
  ```bash
  ./run_workflow.sh -a
  ```

- **Display help**:
  ```bash
  ./run_workflow.sh -h
  ```

### Example Usage

1. **Run the Go program and visualization script together**:
   ```bash
   ./run_workflow.sh -gv
   ```

   This will execute the Go program to generate the `trade_ledger.txt` file and then run the visualization script to create the interactive chart.

2. **Run all steps**:
   ```bash
   ./run_workflow.sh -a
   ```

   This will execute the entire workflow, starting with data collection, followed by the Go program, and finally the visualization script. This is not recommended to run after the initial data collection step has already executed.

### Output

The script will print status messages to the console as it runs. Upon successful completion, it will create an interactive HTML file named `portfolio_performance.html` in the same directory. You can open this file in any web browser to view your portfolio's performance. VS Code's Live Server plugin is especially useful for this. 
