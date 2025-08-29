import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DATA_DIR = "./generated_data/"
RISK_FREE_RATE = 0.02
# Approximate number of trading days in a year
TRADING_DAYS_PER_YEAR = 252

def calculate_performance_metrics(
    portfolio_values: pd.Series,
    benchmark_values: pd.Series,
    management_fee: float,
    performance_fee: float
):
    """
    Calculates key performance metrics (Alpha, Beta, Sharpe Ratio) for a given
    set of portfolio values, applying management and performance fees.
    """
    # --- 1. Apply Fees to Calculate Net Portfolio Values ---
    net_portfolio_values = portfolio_values.copy()
    
    # Apply daily management fee
    daily_management_fee = (1 + management_fee)**(1/TRADING_DAYS_PER_YEAR) - 1
    for i in range(1, len(net_portfolio_values)):
        net_portfolio_values.iloc[i] -= net_portfolio_values.iloc[i-1] * daily_management_fee

    # Calculate total returns before performance fee
    total_algo_return_gross = (net_portfolio_values.iloc[-1] / net_portfolio_values.iloc[0]) - 1
    total_benchmark_return = (benchmark_values.iloc[-1] / benchmark_values.iloc[0]) - 1

    # Apply performance fee on alpha (excess return)
    excess_return = total_algo_return_gross - total_benchmark_return
    if excess_return > 0:
        performance_fee_amount = excess_return * performance_fee * net_portfolio_values.iloc[0] # Apply to initial capital
        net_portfolio_values.iloc[-1] -= performance_fee_amount

    # --- 2. Calculate Daily Returns ---
    algo_returns = net_portfolio_values.pct_change().dropna()
    benchmark_returns = benchmark_values.pct_change().dropna()

    # --- 3. Calculate Core Metrics (Alpha and Beta) ---
    covariance = algo_returns.cov(benchmark_returns)
    variance = benchmark_returns.var()
    beta = covariance / variance

    # Calculate Alpha (using CAPM)
    num_years = len(net_portfolio_values) / TRADING_DAYS_PER_YEAR
    annualized_algo_return = (net_portfolio_values.iloc[-1] / net_portfolio_values.iloc[0])**(1/num_years) - 1
    annualized_benchmark_return = (benchmark_values.iloc[-1] / benchmark_values.iloc[0])**(1/num_years) - 1
    
    expected_return = RISK_FREE_RATE + beta * (annualized_benchmark_return - RISK_FREE_RATE)
    alpha = annualized_algo_return - expected_return

    # --- 4. Calculate Sharpe Ratio ---
    daily_risk_free_rate = (1 + RISK_FREE_RATE)**(1/TRADING_DAYS_PER_YEAR) - 1
    excess_returns_for_sharpe = algo_returns - daily_risk_free_rate
    
    sharpe_ratio = (excess_returns_for_sharpe.mean() / excess_returns_for_sharpe.std()) * np.sqrt(TRADING_DAYS_PER_YEAR)

    return {
        "Alpha (Annualized)": alpha,
        "Beta": beta,
        "Sharpe Ratio (Annualized)": sharpe_ratio,
        "Annualized Return": annualized_algo_return,
        "Annualized Benchmark Return": annualized_benchmark_return
    }

def visualize_metrics_table(hist_gross, hist_net, synth_gross, synth_net, fees):
    """
    Creates a clean HTML table to visualize and compare performance metrics.
    """
    mgmt_fee, perf_fee = fees
    
    fig = go.Figure(data=[go.Table(
        header=dict(values=['<b>Metric</b>', '<b>Historical (Gross)</b>', '<b>Historical (Net)</b>', '<b>Synthetic Median (Gross)</b>', '<b>Synthetic Median (Net)</b>'],
                    fill_color='royalblue',
                    align='left',
                    font=dict(color='white', size=14)),
        cells=dict(values=[
            ['Annualized Return', 'Annualized Benchmark Return', 'Alpha (Annualized)', 'Beta', 'Sharpe Ratio (Annualized)'],
            [f"{hist_gross['Annualized Return']:.2%}", f"{hist_gross['Annualized Benchmark Return']:.2%}", f"{hist_gross['Alpha (Annualized)']:.2%}", f"{hist_gross['Beta']:.2f}", f"{hist_gross['Sharpe Ratio (Annualized)']:.2f}"],
            [f"{hist_net['Annualized Return']:.2%}", f"{hist_net['Annualized Benchmark Return']:.2%}", f"{hist_net['Alpha (Annualized)']:.2%}", f"{hist_net['Beta']:.2f}", f"{hist_net['Sharpe Ratio (Annualized)']:.2f}"],
            [f"{synth_gross['Annualized Return']:.2%}", f"{synth_gross['Annualized Benchmark Return']:.2%}", f"{synth_gross['Alpha (Annualized)']:.2%}", f"{synth_gross['Beta']:.2f}", f"{synth_gross['Sharpe Ratio (Annualized)']:.2f}"],
            [f"{synth_net['Annualized Return']:.2%}", f"{synth_net['Annualized Benchmark Return']:.2%}", f"{synth_net['Alpha (Annualized)']:.2%}", f"{synth_net['Beta']:.2f}", f"{synth_net['Sharpe Ratio (Annualized)']:.2f}"]
        ],
        fill_color='lavender',
        align='left',
        font=dict(color='black', size=12))
    )])

    fig.update_layout(
        title_text=f'<b>Performance Metrics Summary</b><br>(Fees: {mgmt_fee*100:.1f}% Management & {perf_fee*100:.1f}% Performance)',
        height=400
    )

    plot_dir = os.path.join(DATA_DIR, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    output_file = os.path.join(plot_dir, "performance_summary_table.html")
    
    fig.write_html(output_file)
    print(f"\nPerformance summary table saved to '{output_file}'")

def visualize_returns_chart(hist_net, synth_net, fees):
    """
    Creates a bar chart to visualize and compare net annualized returns.
    """
    mgmt_fee, perf_fee = fees
    labels = [
        'Historical Algorithm', 
        'Historical SPY (B&H)', 
        'Median Synthetic Algorithm', 
        'Median Synthetic SPY (B&H)'
    ]
    
    values = [
        hist_net["Annualized Return"],
        hist_net["Annualized Benchmark Return"],
        synth_net["Annualized Return"],
        synth_net["Annualized Benchmark Return"]
    ]

    colors = ['darkgreen', 'black', 'royalblue', 'darkorange']

    fig = go.Figure(data=[go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=[f'{v:.2%}' for v in values],
        textposition='auto'
    )])

    fig.update_layout(
        title_text=f'<b>Net Annualized Returns Comparison</b><br>(After {mgmt_fee*100:.1f}% Mgmt Fee & {perf_fee*100:.1f}% Perf Fee)',
        height=600,
        yaxis_title="Annualized Return",
        yaxis_tickformat='.2%'
    )

    plot_dir = os.path.join(DATA_DIR, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    output_file = os.path.join(plot_dir, "annualized_returns_chart.html")
    
    fig.write_html(output_file)
    print(f"Annualized returns chart saved to '{output_file}'")


def run_analysis(input_file: str, management_fee: float, performance_fee: float):
    """
    Main function to load simulation data and print performance analysis for both
    the historical run and the median of the synthetic simulations.
    """
    # --- 1. Load Data ---
    df = pd.read_csv(input_file)
    df['Date'] = pd.to_datetime(df['Date'])
    print(f"Analyzing data from '{input_file}'...")

    # --- 2. Analyze Historical Performance ---
    print("\n--- Historical Performance Analysis ---")
    historical_df = df[df['Sim_ID'] == 1].copy()
    
    metrics_hist_gross = calculate_performance_metrics(historical_df['Historical_Algo_Value'], historical_df['Historical_SPY_Value'], 0.0, 0.0)
    metrics_hist_net = calculate_performance_metrics(historical_df['Historical_Algo_Value'], historical_df['Historical_SPY_Value'], management_fee, performance_fee)

    # --- 3. Analyze Synthetic (Median) Performance ---
    print("\n--- Synthetic Median Performance Analysis ---")
    median_df = df.groupby('Date')[['Algorithm_Value', 'SPY_Value']].median().reset_index()

    metrics_synth_gross = calculate_performance_metrics(median_df['Algorithm_Value'], median_df['SPY_Value'], 0.0, 0.0)
    metrics_synth_net = calculate_performance_metrics(median_df['Algorithm_Value'], median_df['SPY_Value'], management_fee, performance_fee)
    
    # --- 4. Visualize the Results ---
    visualize_metrics_table(metrics_hist_gross, metrics_hist_net, metrics_synth_gross, metrics_synth_net, (management_fee, performance_fee))
    visualize_returns_chart(metrics_hist_net, metrics_synth_net, (management_fee, performance_fee))


# You can now change the fees and input file directly here
INPUT_FILE = os.path.join(DATA_DIR, "monte_carlo_data_final.csv")
MANAGEMENT_FEE = 0.01  # 1%
PERFORMANCE_FEE = 0.10 # 10%

# Run the analysis with the settings above
run_analysis(INPUT_FILE, MANAGEMENT_FEE, PERFORMANCE_FEE)
