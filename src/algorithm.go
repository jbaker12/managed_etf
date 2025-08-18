package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/go-gota/gota/dataframe"
	"github.com/go-gota/gota/series"
)

// Trade represents a single buy and sell transaction.
type Trade struct {
	Ticker     string
	EntryDate  string
	ExitDate   string
	EntryPrice float64
	ExitPrice  float64
	ProfitLoss float64 // This is now a percentage
	ProfitLossAbs float64 // New field for absolute dollar value
}

// Global constants for the trading strategy
const (
	shortMALength = 50  // Short-term moving average period (50 days)
	longMALength  = 200 // Long-term moving average period (200 days)
	unitSize      = 1000.0 // The dollar amount per trading unit
	initialCapital = 10000.0 // The starting capital for the portfolio
)

// readCSV reads stock data from a specified CSV file into a dataframe.
func readCSV(filePath string) (dataframe.DataFrame, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return dataframe.DataFrame{}, fmt.Errorf("could not open file: %w", err)
	}
	defer file.Close()

	// Read the CSV directly into a dataframe.
	// Gota automatically detects headers and the data types of the columns.
	df := dataframe.ReadCSV(file)

	// Check if the dataframe is empty after reading
	if df.Nrow() == 0 {
		return df, fmt.Errorf("read 0 rows from CSV file")
	}

	return df, nil
}

// calculateMovingAverage computes the simple moving average for a given window using the Close price.
// This function uses a simple sliding window loop, which is a robust way to calculate SMA.
func calculateMovingAverage(dataSeries series.Series, window int) series.Series {
	if dataSeries.Len() < window {
		return series.New([]float64{}, series.Float, "SMA")
	}

	var sma []float64
	// Initialize with zeros for the period before the first full window
	for i := 0; i < window-1; i++ {
		sma = append(sma, 0.0)
	}

	var sum float64
	// Calculate the sum for the first window
	for i := 0; i < window; i++ {
		sum += dataSeries.Elem(i).Float()
	}
	sma = append(sma, sum/float64(window))

	// Slide the window and update the sum for subsequent averages
	for i := window; i < dataSeries.Len(); i++ {
		sum += dataSeries.Elem(i).Float() - dataSeries.Elem(i-window).Float()
		sma = append(sma, sum/float64(window))
	}

	return series.New(sma, series.Float, "SMA")
}

// backtestStrategy runs the moving average crossover algorithm and returns a summary of trades.
func backtestStrategy(df dataframe.DataFrame, ticker string) []Trade {
	// Check for required columns before proceeding. The names are all caps.
	// We'll check if the column names exist in the dataframe's list of names.
	requiredCols := []string{"DATE", "OPEN", "CLOSE"}
	dfColNames := df.Names()
	colMap := make(map[string]bool)
	for _, name := range dfColNames {
		colMap[name] = true
	}

	for _, col := range requiredCols {
		if !colMap[col] {
			fmt.Printf("Error: required column '%s' not found in dataframe. Skipping backtest for this stock.\n", col)
			return nil
		}
	}

	if df.Nrow() < longMALength {
		fmt.Println("Not enough data to perform backtest.")
		return nil
	}

	// Get the 'CLOSE', 'OPEN', and 'DATE' price series for our calculations
	closePriceSeries := df.Col("CLOSE")
	openPriceSeries := df.Col("OPEN")
	dateSeries := df.Col("DATE")

	// Calculate the moving averages
	shortMA := calculateMovingAverage(closePriceSeries, shortMALength)
	longMA := calculateMovingAverage(closePriceSeries, longMALength)

	var trades []Trade
	var currentTrade *Trade = nil

	// Start iterating after the long MA has enough data to be calculated
	for i := longMALength; i < df.Nrow(); i++ {
		// Get values for current and previous day
		currentShortMA := shortMA.Elem(i).Float()
		prevShortMA := shortMA.Elem(i-1).Float()
		currentLongMA := longMA.Elem(i).Float()
		prevLongMA := longMA.Elem(i-1).Float()

		// Buy signal: short MA crosses above long MA
		if currentShortMA > currentLongMA && prevShortMA <= prevLongMA {
			if currentTrade == nil {
				entryPrice := openPriceSeries.Elem(i).Float()
				entryDate := dateSeries.Elem(i).String()
				currentTrade = &Trade{
					Ticker:     ticker,
					EntryDate:  entryDate,
					EntryPrice: entryPrice,
				}
			}
		}

		// Sell signal: short MA crosses below long MA
		if currentShortMA < currentLongMA && prevShortMA >= prevLongMA {
			if currentTrade != nil {
				exitPrice := openPriceSeries.Elem(i).Float()
				exitDate := dateSeries.Elem(i).String()

				// Calculate number of shares
				numShares := unitSize / currentTrade.EntryPrice

				// Calculate absolute profit/loss
				profit := (exitPrice - currentTrade.EntryPrice) * numShares

				currentTrade.ExitDate = exitDate
				currentTrade.ExitPrice = exitPrice
				currentTrade.ProfitLoss = (exitPrice - currentTrade.EntryPrice) / currentTrade.EntryPrice
				currentTrade.ProfitLossAbs = profit
				trades = append(trades, *currentTrade)
				currentTrade = nil // Reset for the next trade
			}
		}
	}

	// Close any open trades at the end of the data
	if currentTrade != nil {
		exitPrice := openPriceSeries.Elem(df.Nrow() - 1).Float()
		exitDate := dateSeries.Elem(df.Nrow() - 1).String()
		numShares := unitSize / currentTrade.EntryPrice
		profit := (exitPrice - currentTrade.EntryPrice) * numShares

		currentTrade.ExitDate = exitDate
		currentTrade.ExitPrice = exitPrice
		currentTrade.ProfitLoss = (exitPrice - currentTrade.EntryPrice) / currentTrade.EntryPrice
		currentTrade.ProfitLossAbs = profit
		trades = append(trades, *currentTrade)
	}

	return trades
}

// findCSVs searches a directory for files ending in .csv and returns their full paths.
func findCSVs(dirPath string) ([]string, error) {
	files, err := os.ReadDir(dirPath)
	if err != nil {
		return nil, fmt.Errorf("could not read directory: %w", err)
	}

	var csvFiles []string
	for _, file := range files {
		if !file.IsDir() && filepath.Ext(file.Name()) == ".csv" {
			csvFiles = append(csvFiles, filepath.Join(dirPath, file.Name()))
		}
	}
	return csvFiles, nil
}

func main() {
	// The path to your directory containing the CSV files.
	const dataDir = "../collected_data"

	// Find all CSV files in the specified directory.
	fmt.Printf("Searching for CSV files in %s...\n", dataDir)
	files, err := findCSVs(dataDir)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("Found %d CSV files.\n", len(files))
	fmt.Println("----------------------------------------")

	// Store results to present a final summary and a complete ledger
	results := make(map[string]float64)
	var allTrades []Trade

	// Loop through each file and run the backtest.
	for _, filePath := range files {
		// Extract the ticker from the filename
		baseName := filepath.Base(filePath)
		ticker := strings.TrimSuffix(baseName, "_yahoo_finance.csv")

		fmt.Printf("Reading data for ticker: %s\n", ticker)
		df, err := readCSV(filePath)
		if err != nil {
			fmt.Printf("Error reading data for %s: %v\n", ticker, err)
			continue
		}

		fmt.Printf("Successfully read %d days of data for %s.\n", df.Nrow(), ticker)
		
		trades := backtestStrategy(df, ticker)

		if len(trades) > 0 {
			var totalProfitLoss float64
			var winningTrades int
			for _, trade := range trades {
				totalProfitLoss += trade.ProfitLossAbs
				if trade.ProfitLossAbs > 0 {
					winningTrades++
				}
			}

			fmt.Printf("\n--- Backtest Summary for %s ---\n", ticker)
			fmt.Printf("Total Trades: %d\n", len(trades))
			fmt.Printf("Total P/L: $%.2f\n", totalProfitLoss)
			fmt.Printf("Win Rate: %.2f%%\n", float64(winningTrades)/float64(len(trades))*100)
			fmt.Println("----------------------------------------")
			results[ticker] = totalProfitLoss
			allTrades = append(allTrades, trades...)
		} else {
			fmt.Printf("No trades were executed with this strategy for %s.\n", ticker)
			fmt.Println("-----------------")
		}
	}

	// Final summary of all backtested stocks
	if len(results) > 0 {
		fmt.Println("\n--- Final Summary: Most Profitable Stocks ---")
		// Simple in-memory sorting of results to show top performers
		type StockResult struct {
			Ticker string
			Profit float64
		}
		var sortedResults []StockResult
		for ticker, profit := range results {
			sortedResults = append(sortedResults, StockResult{Ticker: ticker, Profit: profit})
		}
		
		// Sort the slice by profit in descending order
		sort.Slice(sortedResults, func(i, j int) bool {
			return sortedResults[i].Profit > sortedResults[j].Profit
		})

		for _, result := range sortedResults {
			fmt.Printf("%s: $%.2f\n", result.Ticker, result.Profit)
		}
	}

	// Print a detailed ledger of all trades to a file
	if len(allTrades) > 0 {
		fmt.Println("\n\n--- Writing Trade Ledger to File ---")
		
		file, err := os.Create("./generated_data/trade_ledger.txt")
		if err != nil {
			fmt.Println("Error creating ledger file:", err)
			return
		}
		defer file.Close()
		
		writer := bufio.NewWriter(file)
		
		// Sort trades by entry date to present them chronologically
		sort.Slice(allTrades, func(i, j int) bool {
			return allTrades[i].EntryDate < allTrades[j].EntryDate
		})
		
		// Write the header with portfolio value.
		fmt.Fprintf(writer, "%-10s | %-12s | %-12s | %-12s | %-12s | %-12s | %-15s\n", "Ticker", "Entry Date", "Exit Date", "Entry Price", "Exit Price", "P/L %", "P/L ($)")
		fmt.Fprintln(writer, strings.Repeat("-", 100))

		// Write each trade to the file.
		for _, trade := range allTrades {
			fmt.Fprintf(writer, "%-10s | %-12s | %-12s | %-12.2f | %-12.2f | %-12.2f%% | %-15.2f\n", 
				trade.Ticker,
				trade.EntryDate,
				trade.ExitDate,
				trade.EntryPrice,
				trade.ExitPrice,
				trade.ProfitLoss*100,
				trade.ProfitLossAbs,
			)
		}
		
		writer.Flush()
	}
}
