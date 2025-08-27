import argparse
import os
import pandas as pd
import time
import random
import concurrent.futures

import data_collection as dc


# Define a directory to save the collected data
DATA_DIR = "../collected_data"

SP500_TICKERS = [
    "SPY", # For S&P 500 ETF
    "A", "AAL", "AAP", "AAPL", "ABBV", "ABC", "ABT", "ACGL", "ACN",
    "ADBE", "ADI", "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG",
    "AIZ", "AJG", "AKAM", "ALB", "ALGN", "ALK", "ALL", "ALLE", "AMAT", "AMCR",
    "AMD", "AME", "AMGN", "AMP", "AMT", "AMZN", "ANET", "ANSS", "AON", "AOS",
    "APA", "APD", "APH", "APTV", "ARE", "ATO", "AVB", "AVGO", "AVY", "AWK",
    "AXON", "AXP", "AZO", "BA", "BAC", "BALL", "BAX", "BBWI", "BBY", "BDX",
    "BEN", "BF-B", "BIIB", "BIO", "BK", "BKNG", "BKR", "BLK", "BMY", "BR",
    "BRK-B", "BRO", "BSX", "BWA", "BX", "BXP", "C", "CAG", "CAH", "CARR",
    "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL", "CDNS", "CDW", "CE", "CEG",
    "CF", "CFG", "CHD", "CHRW", "CHTR", "CI", "CINF", "CL", "CLX", "CMA",
    "CMCSA", "CME", "CMG", "CMI", "CMS", "CNC", "CNP", "COF", "COO", "COP",
    "COR", "COST", "CPB", "CPRT", "CPT", "CRM", "CSCO", "CSGP", "CSX", "CTAS",
    "CTLT", "CTRA", "CTSH", "CVS", "CVX", "D", "DAL", "DD", "DE", "DECK",
    "DFS", "DG", "DGX", "DHI", "DHR", "DIS", "DLR", "DLTR", "DOV", "DOW",
    "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN", "DXCM", "EA", "EBAY", "ECL",
    "ED", "EFX", "EIX", "EL", "ELV", "EMN", "EMR", "ENPH", "EOG", "EPAM",
    "EQIX", "EQR", "EQT", "ERIE", "ES", "ESS", "ETN", "ETR", "ETSY", "EVRG",
    "EW", "EXC", "EXPD", "EXPE", "EXR", "F", "FANG", "FAST", "FCX", "FDS",
    "FDX", "FE", "FFIV", "FI", "FICO", "FIS", "FITB", "FLT", "FMC", "FOX",
    "FOXA", "FRT", "FSLR", "FTNT", "FTV", "GD", "GE", "GEHC", "GEN", "GILD",
    "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN", "GRMN",
    "GS", "GWW", "HAL", "HAS", "HBAN", "HCA", "HD", "HES", "HIG", "HII",
    "HLT", "HOLX", "HON", "HPE", "HPQ", "HRL", "HSIC", "HST", "HSY", "HUBB",
    "HUM", "HWM", "IBM", "ICE", "IDXX", "IEX", "IFF", "ILMN", "INCY", "INTC",
    "INTU", "INVH", "IP", "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW",
    "IVZ", "J", "JBHT", "JCI", "JKHY", "JNJ", "JNPR", "JPM", "K", "KDP",
    "KEY", "KEYS", "KHC", "KIM", "KLAC", "KMB", "KMI", "KMX", "KO", "KR",
    "KVUE", "L", "LDOS", "LEN", "LH", "LHX", "LIN", "LKQ", "LLY", "LMT",
    "LNT", "LOW", "LRCX", "LULU", "LUV", "LVS", "LW", "LYB", "LYV", "MA",
    "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET",
    "META", "MGM", "MHK", "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST", "MO",
    "MOH", "MOS", "MPC", "MPWR", "MRK", "MRNA", "MRO", "MS", "MSCI", "MSFT",
    "MSI", "MTB", "MTD", "MU", "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX",
    "NI", "NKE", "NOC", "NOW", "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA",
    "NVR", "NWS", "NWSA", "NXPI", "O", "ODFL", "OGN", "OKE", "OMC", "ON",
    "ORCL", "ORLY", "OTIS", "OXY", "PANW", "PARA", "PAYC", "PAYX", "PCAR",
    "PCG", "PEG", "PEP", "PFE", "PFG", "PG", "PGR", "PH", "PHM", "PKG",
    "PLD", "PM", "PNC", "PNR", "PNW", "PODD", "POOL", "PPG", "PPL", "PRU",
    "PSA", "PSX", "PTC", "PWR", "PXD", "PYPL", "QCOM", "QRVO", "RCL", "REG",
    "REGN", "RF", "RHI", "RJF", "RL", "RMD", "ROK", "ROL", "ROP", "ROST",
    "RSG", "RTX", "RVTY", "SBAC", "SBUX", "SCHW", "SHW", "SJM", "SLB", "SNA",
    "SNPS", "SO", "SPG", "SPGI", "SRE", "STE", "STT", "STX", "STZ", "SWK",
    "SWKS", "SYF", "SYK", "SYY", "T", "TAP", "TDG", "TDY", "TECH", "TFC",
    "TFX", "TGT", "TJX", "TMO", "TMUS", "TPR", "TRGP", "TRMB", "TROW", "TRV",
    "TSCO", "TSLA", "TT", "TTWO", "TXN", "TXT", "TYL", "UAL", "UDR", "UHS",
    "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V", "VFC", "VLO", "VMC",
    "VRSK", "VRSN", "VRT", "VTR", "VTRS", "VZ", "WAB", "WAT", "WBA", "WBD",
    "WCN", "WDC", "WEC", "WELL", "WFC", "WHR", "WM", "WMB", "WMT", "WRB",
    "WRK", "WST", "WTW", "WY", "WYNN", "XEL", "XOM", "XRAY", "XYL", "YUM",
    "ZBH", "ZBRA", "ZTS"
]

def collect_data_for_ticker(ticker, start_date, end_date):
    """
    Collects financial data for a single ticker using Yahoo Finance. This function will be run in a separate thread.
    Returns True if successful, False if failed.
    """
    print(f"\n--- Collecting data for {ticker} ---")

    try:
        # Collect Yahoo Finance Data
        print(f"Fetching Yahoo Finance data for {ticker}...")
        yahoo_finance_df = dc.get_yahoo_finance_data(ticker, start_date, end_date)
        if yahoo_finance_df is not None:
            yahoo_finance_file_path = os.path.join(DATA_DIR, f"{ticker}_yahoo_finance.csv")
            yahoo_finance_df.to_csv(yahoo_finance_file_path, index=False)
            print(f"Yahoo Finance data saved to {yahoo_finance_file_path}")
            return True  # Success
        else:
            print(f"No Yahoo Finance data found for {ticker}.")
            return False  # Failure
    except Exception as exc:
        print(f"Error collecting data for {ticker}: {exc}")
        return False  # Failure
    finally:
        time.sleep(random.uniform(1, 3))  # Add a small delay to avoid overwhelming the API


def main():
    """
    Main function to parse arguments and orchestrate data collection for S&P 500 stocks using threads.
    """
    parser = argparse.ArgumentParser(description="Collect financial data for S&P 500 stocks using multiple threads.")
    parser.add_argument("--start_date", type=str, default="1999-01-01", help="Start date for historical data (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, default="2025-07-01", help="End date for historical data (YYYY-MM-DD)")
    parser.add_argument("--max_workers", type=int, default=5, help="Maximum number of worker threads to use for data collection")

    args = parser.parse_args()

    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)

    tickers = SP500_TICKERS

    if not tickers:
        print("No S&P 500 tickers found in the hardcoded list. Exiting data collection.")
        return

    print(f"Starting data collection for {len(tickers)} S&P 500 stocks using {args.max_workers} threads.")
    print(f"Date range: {args.start_date} to {args.end_date}")

    failed_tickers = [] 

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_ticker = {
            executor.submit(
                collect_data_for_ticker,
                ticker,
                args.start_date,
                args.end_date
            ): ticker for ticker in tickers
        }

        # Iterate over completed futures to see results
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                future.result()
            except Exception as exc:
                print(f'{ticker} generated an exception: {exc}')
                failed_tickers.append(ticker) 

    # Save failed tickers to a file
    if failed_tickers:
        failed_tickers_file = os.path.join(DATA_DIR, "failed_tickers.txt")
        with open(failed_tickers_file, "w") as f:
            f.write("\n".join(failed_tickers))
        print(f"\nFailed tickers saved to {failed_tickers_file}")

    print("\nData collection complete!")
    print(f"All collected data is stored in the '{DATA_DIR}' directory.")


if __name__ == "__main__":
    main()
