import argparse
import os
import pandas as pd
import time
import random
import concurrent.futures

import data_collection as dc


# Define a directory to save the collected data
DATA_DIR = "collected_data"

SP500_TICKERS = [
    "MMM", "AOS", "ABT", "ABBV", "ACN", "ADBE", "AMD", "AES", "AFL", "A", "APD",
    "ABNB", "AKAM", "ALB", "ARE", "ALGN", "ALLE", "LNT", "ALL", "GOOGL", "GOOG",
    "MO", "AMZN", "AMCR", "AEE", "AEP", "AXP", "AIG", "AMT", "AWK", "AMP", "AME",
    "AMGN", "APH", "ADI", "ANSS", "AON", "APA", "APO", "AAPL", "AMAT", "APTV",
    "ARCH", "ARNC", "ATO", "ATVI", "ADSK", "AZO", "AVB", "AVY", "BKR", "BAX",
    "BDX", "BRK.B", "BBY", "BIO", "BIIB", "BLK", "BX", "BAC", "BBWI", "BA",
    "BK", "BN", "BXP", "BSX", "BMY", "AVGO", "BR", "BRO", "BF.B", "BF.A",
    "CPB", "COF", "CAH", "KMX", "CCL", "CARR", "CAT", "CBOE", "CDNS", "CDW",
    "CE", "CNC", "CNP", "CDAY", "CERN", "CF", "CRL", "SCHW", "CHTR", "CVX",
    "CMG", "CB", "CHD", "CI", "CINF", "CTAS", "C", "CLX", "CME", "CMS", "KO",
    "CTSH", "CL", "CMCSA", "CAG", "COP", "STZ", "CEG", "COR", "CSGP", "CMA",
    "CSC", "CMCSA", "CACC", "CSX", "CTLT", "CVS", "DHR", "DRI", "DVA", "DE",
    "DAL", "XRAY", "DVN", "DXCM", "FANG", "DLR", "DFS", "DIS", "DG", "DLTR",
    "D", "DPZ", "DOV", "DOW", "DTE", "DUK", "DD", "EMN", "ETN", "EBAY", "ECL",
    "EIX", "EW", "EA", "EMR", "ENPH", "ETR", "EOG", "EQIX", "EQT", "ES", "ESS",
    "ELV", "ETSY", "EVRG", "ESRX", "EXC", "EXPE", "EXPD", "XOM", "FDS", "FAST",
    "FRT", "FDX", "FE", "FIS", "FITB", "FMC", "F", "FTNT", "FTV", "FOXA", "FOX",
    "BEN", "FCX", "GRMN", "IT", "GD", "GE", "GIS", "GM", "GPC", "GILD", "GLW",
    "GOOG", "GOOGL", "GPN", "GPS", "GRMN", "GS", "HAL", "HBI", "HAS", "HCA",
    "PEAK", "HSIC", "HES", "HWM", "HP", "HST", "HRL", "HLT", "HOLX", "HD",
    "HON", "HPE", "HPQ", "HUM", "HII", "IBM", "IEX", "IDXX", "IFF", "ILMN",
    "INCY", "IR", "INTC", "ICE", "IBM", "IP", "IPG", "INTU", "ISRG", "IVZ",
    "IRM", "JBL", "JKHY", "J", "JPM", "JNJ", "KSU", "K", "KVUE", "KMB", "KMI",
    "KLAC", "KSS", "KR", "LHX", "LRCX", "LW", "LVS", "LEG", "LEN", "LLY", "LNC",
    "LIN", "LYV", "LKQ", "LMT", "L", "LOW", "LULU", "MAR", "MMC", "MLM", "MAS",
    "MA", "MKC", "MCD", "MCK", "MDT", "MRK", "META", "MET", "MIK", "MSFT",
    "MCO", "MPC", "MDLZ", "MNST", "MORG", "MSI", "MS", "MOS", "MSCI", "NDAQ",
    "NEE", "NEM", "NFLX", "NWSA", "NWS", "NI", "NKE", "NOC", "NLOK", "NCLH",
    "NRG", "NUE", "NVDA", "NVR", "NXPI", "ORLY", "OXY", "ODFL", "OMC", "OKE",
    "ORCL", "OGN", "OTIS", "PCAR", "PKG", "PANW", "PARA", "PAYC", "PAYX", "PCG",
    "PEP", "PFE", "PM", "PSX", "PNR", "PBCT", "PGR", "PLD", "PNC", "POOL",
    "PPG", "PPL", "PFG", "PG", "PGR", "PRU", "PEG", "PSA", "PHM", "PVH", "QRVO",
    "PWR", "QCOM", "DGX", "RL", "RJF", "RTX", "O", "REGN", "RF", "RSG", "RMD",
    "RHI", "ROK", "ROL", "ROP", "ROST", "RCL", "SPGI", "CRM", "SBAC", "SLB",
    "STX", "SEE", "SRE", "NOW", "SHW", "SPG", "SWKS", "SJM", "SNA", "SO", "LUV",
    "SWK", "SBUX", "STT", "STE", "SYK", "SYF", "SNPS", "SYY", "TMUS", "TROW",
    "TTWO", "TPR", "TGT", "TEL", "TDY", "TFX", "TXN", "TXT", "TMO", "TJX", "TSLA",
    "TXN", "TMO", "TJX", "TSLA", "TRV", "TRMB", "TFC", "TWTR", "TYL", "UDR",
    "ULTA", "UNP", "UAL", "UNH", "UPS", "URI", "UHS", "VLO", "VAR", "VTR", "VRSK",
    "VRSN", "V", "VNO", "VMC", "WAB", "WBA", "WMT", "WBD", "WM", "WAT", "WEC",
    "WFC", "WELL", "WST", "WDC", "WRK", "WY", "WHR", "WMB", "WLTW", "WYNN", "XEL",
    "XLNX", "XYL", "YUM", "ZBH", "ZION", "ZTS"
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
            yahoo_finance_df.to_csv(yahoo_finance_file_path, index=True)
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
    parser.add_argument("--start_date", type=str, default="2023-01-01", help="Start date for historical data (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, default="2024-01-01", help="End date for historical data (YYYY-MM-DD)")
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
                # Get the result of the future 
                future.result()
            except Exception as exc:
                print(f'{ticker} generated an exception: {exc}')
                failed_tickers.append(ticker)  # Add failed ticker to the list

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
