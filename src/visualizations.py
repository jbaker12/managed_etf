import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# --- Configuration ---
INPUT_CSV_FILE = "./generated_data/monte_carlo_data_final.csv"
OUTPUT_HTML_FILE = "./generated_data/plots/monte_carlo_analysis_final.html"

def create_fan_chart():
    """
    Reads Monte Carlo data and generates an interactive fan chart
    showing confidence intervals for the algorithm and SPY simulations.
    """
    # --- 1. Load and Process Data ---
    try:
        df = pd.read_csv(INPUT_CSV_FILE)
    except FileNotFoundError:
        print(f"Error: The data file '{INPUT_CSV_FILE}' was not found.")
        print("Please run the Go program first to generate the simulation data.")
        return

    df['Date'] = pd.to_datetime(df['Date'])
    print(f"Successfully loaded {df['Sim_ID'].nunique()} simulations from '{INPUT_CSV_FILE}'.")

    # --- 2. Calculate Percentiles for Fan Chart ---
    # Group by date and calculate the required percentiles for both simulation types
    percentiles = df.groupby('Date')[['Algorithm_Value', 'SPY_Value']].quantile([0.05, 0.25, 0.5, 0.75, 0.95]).unstack()

    # --- 3. Create the Plotly Figure ---
    fig = go.Figure()
    pio.templates.default = "plotly_white"

    # --- 4. Plot Confidence Bands and Median for Algorithm (Blue) ---
    # 90% Confidence Interval (5th to 95th percentile) - Lighter Shade
    fig.add_trace(go.Scatter(
        x=percentiles.index, y=percentiles[('Algorithm_Value', 0.95)],
        mode='lines', line=dict(width=0), showlegend=False, hoverinfo='none'
    ))
    fig.add_trace(go.Scatter(
        x=percentiles.index, y=percentiles[('Algorithm_Value', 0.05)],
        mode='lines', line=dict(width=0), fill='tonexty',
        fillcolor='rgba(0, 123, 255, 0.2)', name='Algo 90% CI', hoverinfo='none'
    ))

    # 50% Confidence Interval (25th to 75th percentile) - Darker Shade
    fig.add_trace(go.Scatter(
        x=percentiles.index, y=percentiles[('Algorithm_Value', 0.75)],
        mode='lines', line=dict(width=0), showlegend=False, hoverinfo='none'
    ))
    fig.add_trace(go.Scatter(
        x=percentiles.index, y=percentiles[('Algorithm_Value', 0.25)],
        mode='lines', line=dict(width=0), fill='tonexty',
        fillcolor='rgba(0, 123, 255, 0.4)', name='Algo 50% CI', hoverinfo='none'
    ))

    # Median Line for Algorithm
    fig.add_trace(go.Scatter(
        x=percentiles.index, y=percentiles[('Algorithm_Value', 0.5)],
        mode='lines', name='Median Synthetic Algorithm',
        line=dict(color='blue', width=2),
        hovertemplate='<b>Median Synthetic Algo</b><br>Date: %{x|%Y-%m-%d}<br>Value: $%{y:,.2f}<extra></extra>'
    ))

    # --- 5. Plot Confidence Bands and Median for Synthetic SPY (Orange) ---
    # 90% Confidence Interval (5th to 95th percentile) - Lighter Shade
    fig.add_trace(go.Scatter(
        x=percentiles.index, y=percentiles[('SPY_Value', 0.95)],
        mode='lines', line=dict(width=0), showlegend=False, hoverinfo='none'
    ))
    fig.add_trace(go.Scatter(
        x=percentiles.index, y=percentiles[('SPY_Value', 0.05)],
        mode='lines', line=dict(width=0), fill='tonexty',
        fillcolor='rgba(255, 165, 0, 0.2)', name='SPY 90% CI', hoverinfo='none'
    ))

    # 50% Confidence Interval (25th to 75th percentile) - Darker Shade
    fig.add_trace(go.Scatter(
        x=percentiles.index, y=percentiles[('SPY_Value', 0.75)],
        mode='lines', line=dict(width=0), showlegend=False, hoverinfo='none'
    ))
    fig.add_trace(go.Scatter(
        x=percentiles.index, y=percentiles[('SPY_Value', 0.25)],
        mode='lines', line=dict(width=0), fill='tonexty',
        fillcolor='rgba(255, 165, 0, 0.4)', name='SPY 50% CI', hoverinfo='none'
    ))

    # Median Line for SPY
    fig.add_trace(go.Scatter(
        x=percentiles.index, y=percentiles[('SPY_Value', 0.5)],
        mode='lines', name='Median Synthetic SPY (B&H)',
        line=dict(color='darkorange', width=1.5),
        hovertemplate='<b>Median Synthetic SPY</b><br>Date: %{x|%Y-%m-%d}<br>Value: $%{y:,.2f}<extra></extra>'
    ))


    # --- 6. Plot Historical Performance Lines ---
    historical_df = df.groupby('Date')[['Historical_Algo_Value', 'Historical_SPY_Value']].mean().reset_index()

    fig.add_trace(go.Scatter(
        x=historical_df['Date'], y=historical_df['Historical_Algo_Value'],
        mode='lines', name='Historical Algorithm',
        line=dict(color='darkgreen', width=2),
        hovertemplate='<b>Historical Algo</b><br>Date: %{x|%Y-%m-%d}<br>Value: $%{y:,.2f}<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=historical_df['Date'], y=historical_df['Historical_SPY_Value'],
        mode='lines', name='Historical SPY (B&H)',
        line=dict(color='black', width=2),
        hovertemplate='<b>Historical SPY</b><br>Date: %{x|%Y-%m-%d}<br>Value: $%{y:,.2f}<extra></extra>'
    ))

    # --- 7. Customize and Save the Plot ---
    fig.update_layout(
        title={
            'text': '<b>Monte Carlo Simulation: Performance Confidence Intervals</b>',
            'y':0.95, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top', 'font': {'size': 22}
        },
        xaxis_title='Date',
        yaxis_title='Portfolio Value ($)',
        yaxis_tickprefix='$', yaxis_tickformat=',.0f',
        legend=dict(x=0.01, y=0.99, xanchor='left', yanchor='top', bgcolor='rgba(255, 255, 255, 0.8)'),
        height=900,
        # yaxis=dict(
        #     range=[0, 1000000],
        #     tickprefix='$',
        #     tickformat=',.0f'
        # ),
        hovermode='x unified'
    )

    fig.write_html(OUTPUT_HTML_FILE)
    print(f"\nInteractive fan chart saved successfully to '{OUTPUT_HTML_FILE}'")


if __name__ == "__main__":
    create_fan_chart()
