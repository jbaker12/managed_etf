#!/bin/bash

# Define paths to scripts and files
DATA_COLLECTION_SCRIPT="driver.py"
GO_PROGRAM="algorithm.go"
VISUALIZATION_SCRIPT="visualizations.py"
TRADE_LEDGER="./generated_data/trade_ledger.txt"

# Function to display usage instructions
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -d    Run the data collection script (driver.py)"
    echo "  -g    Run the Go program (algorithm.go)"
    echo "  -v    Run the visualization script (visualizations.py)"
    echo "  -gv   Run the Go program and visualization script together"
    echo "  -a    Run all steps (data collection, Go program, and visualization)"
    echo "  -h    Display this help message"
    exit 1
}

# Function to run the data collection script
run_data_collection() {
    echo "Running data collection script..."
    python3 "$DATA_COLLECTION_SCRIPT"
    if [ $? -eq 0 ]; then
        echo "Data collection completed successfully."
    else
        echo "Error: Data collection script failed."
        exit 1
    fi
}

# Function to run the Go program
run_go_program() {
    echo "Running Go program..."
    go run "$GO_PROGRAM"
    if [ $? -eq 0 ]; then
        echo "Go program executed successfully."
    else
        echo "Error: Go program failed."
        exit 1
    fi
}

# Function to run the visualization script
run_visualization() {
    echo "Running visualization script..."
    if [ ! -f "$TRADE_LEDGER" ]; then
        echo "Error: Trade ledger file '$TRADE_LEDGER' not found. Please run the Go program first."
        exit 1
    fi
    python3 "$VISUALIZATION_SCRIPT"
    if [ $? -eq 0 ]; then
        echo "Visualization completed successfully."
    else
        echo "Error: Visualization script failed."
        exit 1
    fi
}

# Function to run the Go program and visualization script together
run_go_and_visualization() {
    run_go_program
    run_visualization
}

# Parse command-line options
if [ $# -eq 0 ]; then
    usage
fi

while getopts "dgvah" opt; do
    case $opt in
        d)
            run_data_collection
            ;;
        g)
            run_go_program
            ;;
        v)
            run_visualization
            ;;
        gv)
            run_go_and_visualization
            ;;
        a)
            run_data_collection
            run_go_program
            run_visualization
            ;;
        h)
            usage
            ;;
        *)
            usage
            ;;
    esac
done