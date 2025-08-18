# A script to visualize portfolio value over time from a trade ledger using Plotly.
import pandas as pd
import plotly.graph_objects as go
import os
import plotly.express as px

def load_and_process_ledger(ledger_file: str):
    """
    Loads the trade ledger file, cleans the data, and returns a processed DataFrame.
    """
    try:
        df = pd.read_csv(
            ledger_file,
            sep="|",
            skiprows=2,
            header=None,
            names=["Ticker", "Entry Date", "Exit Date", "Entry Price", "Exit Price", "P/L %", "P/L ($)"]
        )

        # Clean up whitespace and convert data types.
        df.columns = df.columns.str.strip()
        df['Entry Price'] = pd.to_numeric(df['Entry Price'].astype(str).str.strip(), errors='coerce')
        df['Exit Price'] = pd.to_numeric(df['Exit Price'].astype(str).str.strip(), errors='coerce')
        df['P/L %'] = pd.to_numeric(df['P/L %'].astype(str).str.strip().str.replace('%', ''), errors='coerce') / 100
        df['P/L ($)'] = pd.to_numeric(df['P/L ($)'].astype(str).str.strip(), errors='coerce')
        df.dropna(subset=['Entry Price', 'Exit Price', 'P/L %', 'P/L ($)'], inplace=True)
        df['Entry Date'] = pd.to_datetime(df['Entry Date'])
        df['Exit Date'] = pd.to_datetime(df['Exit Date'])
        
        return df.sort_values(by='Entry Date')
    
    except FileNotFoundError:
        print(f"Error: The file '{ledger_file}' was not found. Please ensure your Go program has run successfully.")
        return None
    except Exception as e:
        print(f"An error occurred while processing the ledger: {e}")
        return None

def calculate_portfolio_value(df: pd.DataFrame, initial_capital: float):
    """
    Calculates the cumulative portfolio value over time based on trade P/L.
    """
    portfolio_dates = []
    portfolio_values = []
    current_capital = initial_capital
    
    if df.empty:
        return pd.DataFrame({'DATE': [], 'VALUE': []})
        
    first_trade_date = df['Entry Date'].min()
    portfolio_dates.append(first_trade_date)
    portfolio_values.append(current_capital)

    for _, row in df.iterrows():
        current_capital += row['P/L ($)']
        portfolio_dates.append(row['Exit Date'])
        portfolio_values.append(current_capital)
        
    return pd.DataFrame({'DATE': portfolio_dates, 'VALUE': portfolio_values}).sort_values(by='DATE')

def calculate_benchmark_value(spy_df: pd.DataFrame, price_column: str, portfolio_df: pd.DataFrame, initial_capital: float):
    """
    Calculates a single benchmark based on a specified price column.
    
    Args:
        spy_df (pd.DataFrame): The DataFrame containing SPY data.
        price_column (str): The column to use for benchmark calculation ('OPEN' or 'ADJ CLOSE').
        portfolio_df (pd.DataFrame): The DataFrame with the portfolio dates to align with.
        initial_capital (float): The starting capital.
    
    Returns:
        pd.DataFrame: The benchmark DataFrame or None if the column is missing.
    """
    if price_column not in spy_df.columns:
        return None

    initial_price = spy_df[price_column].iloc[0]
    spy_df['SHARES'] = initial_capital / initial_price
    spy_df['BENCHMARK_VALUE'] = spy_df['SHARES'] * spy_df[price_column]

    benchmark_df = pd.DataFrame({
        'DATE': portfolio_df['DATE'],
        'VALUE': [
            spy_df[spy_df['DATE'] <= d]['BENCHMARK_VALUE'].iloc[-1] 
            if not spy_df[spy_df['DATE'] <= d].empty 
            else initial_capital 
            for d in portfolio_df['DATE']
        ]
    })
    return benchmark_df

def calculate_spy_benchmarks(data_dir: str, portfolio_df: pd.DataFrame, initial_capital: float):
    """
    Loads SPY data and calculates the price-only benchmark.
    """
    spy_file_path = os.path.join(data_dir, 'SPY_yahoo_finance.csv')
    
    if not os.path.exists(spy_file_path):
        print(f"Warning: SPY data file not found at '{spy_file_path}'. The SPY benchmark will not be plotted.")
        return None
    
    try:
        spy_df = pd.read_csv(spy_file_path)
        spy_df.columns = spy_df.columns.str.upper().str.strip()
        spy_df['DATE'] = pd.to_datetime(spy_df['DATE'].astype(str).str.strip(), errors='coerce')
        spy_df.dropna(subset=['DATE'], inplace=True)
        spy_df.sort_values(by='DATE', inplace=True)
        
        price_only_df = calculate_benchmark_value(spy_df, 'OPEN', portfolio_df, initial_capital)
        
        return price_only_df

    except Exception as e:
        print(f"An error occurred while processing SPY data: {e}")
        return None


def create_plotly_chart(portfolio_df: pd.DataFrame, benchmark_df: pd.DataFrame, ledger_df: pd.DataFrame):
    """
    Creates and saves an interactive Plotly chart with all the data.
    """
    fig = go.Figure()

    # Add the portfolio performance line.
    fig.add_trace(go.Scatter(
        x=portfolio_df['DATE'], 
        y=portfolio_df['VALUE'], 
        mode='lines+markers', 
        name='Trading Strategy',
        marker=dict(size=5)
    ))

    # Add the "Buy and Hold" benchmark line (price-only).
    if benchmark_df is not None:
        fig.add_trace(go.Scatter(
            x=benchmark_df['DATE'], 
            y=benchmark_df['VALUE'], 
            mode='lines', 
            name='SPY Price Only',
            line=dict(dash='dash', color='red')
        ))
    
    # Add winning and losing trades as separate scatter plots.
    winning_trades = ledger_df[ledger_df['P/L ($)'] > 0]
    losing_trades = ledger_df[ledger_df['P/L ($)'] <= 0]
    
    winning_portfolio_values = []
    losing_portfolio_values = []
    cumulative_pl = 10000.0 # Re-calculate for plot markers
    
    for _, row in ledger_df.iterrows():
        cumulative_pl += row['P/L ($)']
        if row['P/L ($)'] > 0:
            winning_portfolio_values.append(cumulative_pl)
        else:
            losing_portfolio_values.append(cumulative_pl)

    fig.add_trace(go.Scatter(
        x=winning_trades['Exit Date'], 
        y=winning_portfolio_values,
        mode='markers', 
        name='Winning Trade',
        marker=dict(color='green', symbol='triangle-up', size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=losing_trades['Exit Date'], 
        y=losing_portfolio_values,
        mode='markers', 
        name='Losing Trade',
        marker=dict(color='red', symbol='triangle-down', size=8)
    ))
    
    # Customize the layout for better readability.
    fig.update_layout(
        title="Portfolio Performance vs. SPY Benchmark",
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        yaxis_tickprefix="$",
        hovermode="x unified"
    )
    
    # Save the plot as an interactive HTML file.
    output_file = 'portfolio_performance.html'
    fig.write_html(output_file)
    print(f"Interactive portfolio performance chart saved as {output_file}")


def visualize_portfolio_performance(ledger_file: str, initial_capital: float = 10000.0, data_dir: str = '../collected_data'):
    """
    Main function to orchestrate the portfolio visualization process.
    """
    # 1. Load and process the trade ledger
    ledger_df = load_and_process_ledger(ledger_file)
    if ledger_df is None:
        return

    # 2. Calculate the portfolio value over time
    portfolio_df = calculate_portfolio_value(ledger_df, initial_capital)
    if portfolio_df.empty:
        print("No valid trades found in the ledger. Cannot create a performance chart.")
        return

    # 3. Calculate SPY benchmark
    benchmark_df = calculate_spy_benchmarks(data_dir, portfolio_df, initial_capital)

    # 4. Create the final plot and save it
    create_plotly_chart(portfolio_df, benchmark_df, ledger_df)


if __name__ == "__main__":
    visualize_portfolio_performance("./generated_data/trade_ledger.txt", initial_capital=10000.0)
