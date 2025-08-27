package main

import (
	"encoding/csv"
	"fmt"
	// "flag"
	"io/ioutil"
	"log"
	"math"
	"math/rand"
	"os"
	"path/filepath"
	// "runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/go-gota/gota/dataframe"
	"github.com/go-gota/gota/series"
)

// --- Configuration ---
const (
	shortMALength    = 50
	longMALength     = 200
	initialCapital   = 10000.0
	numSimulations   = 100
	dataDirectory    = "../collected_data/"
	outputFile       = "./generated_data/monte_carlo_data_final.csv"
	perTradeRisk     = 0.02 // Risk 2% of capital per trade
	blockSize        = 10   // Size of the block for block bootstrapping
	riskFreeRate     = 0.02 // Annual risk-free interest rate (e.g., 2%)
)

// Trade holds information about a single transaction.
type Trade struct {
	Ticker     string
	EntryDate  time.Time
	ExitDate   time.Time
	EntryPrice float64
	ExitPrice  float64
	Shares     float64
}

// dailyValue holds the portfolio value for a specific day and simulation.
type dailyValue struct {
	Date                time.Time
	AlgorithmValue      float64 // Synthetic Algorithm
	SPYValue            float64 // Synthetic SPY (Buy & Hold)
	HistoricalSPYValue  float64 // Actual SPY (Buy & Hold)
	HistoricalAlgoValue float64 // Actual Algorithm
	SimID               int
}

// --- Main Execution ---

func main() {
	startTime := time.Now()
	rand.Seed(14)
	// seed := flag.Int64("seed", 42, "Random seed for the simulation")
	// flag.Parse()
	// rand.Seed(*seed)
	// // --- CHANGE END ---

	// // --- CHANGE START: Define outputFile using the provided seed ---
	// outputFile := fmt.Sprintf("./generated_data/monte_carlo_data_seed_%d.csv", *seed)
	// // --- CHANGE END ---


	// 1. Load all historical data and separate SPY from the portfolio
	fmt.Println("Loading historical data...")
	allData, err := loadHistoricalData(dataDirectory)
	if err != nil {
		log.Fatalf("Failed to load historical data: %v", err)
	}

	spyHistoricalDF, ok := allData["SPY"]
	if !ok {
		log.Fatal("Critical: SPY_yahoo_finance.csv not found in the data directory.")
	}
	portfolioHistoricalData := make(map[string]dataframe.DataFrame)
	for ticker, df := range allData {
		if ticker != "SPY" {
			portfolioHistoricalData[ticker] = df
		}
	}

	// Load the market caps from the new CSV file
	fmt.Println("Loading market cap data...")
	marketCaps, err := loadMarketCaps(filepath.Join(dataDirectory, "market_caps.csv"))
	if err != nil {
		log.Fatalf("Failed to load market caps: %v", err)
	}
	fmt.Printf("Loaded market caps for %d tickers.\n", len(marketCaps))

	if len(portfolioHistoricalData) == 0 {
		log.Fatal("No portfolio tickers loaded (excluding SPY). Please check data directory.")
	}
	fmt.Printf("Loaded historical data for %d portfolio tickers and SPY.\n", len(portfolioHistoricalData))

	// 2. Run backtests on ACTUAL historical data ONCE
	fmt.Println("Running backtest on historical data...")
	historicalPortfolioWithMAs := precalculateAllMovingAverages(portfolioHistoricalData)
	_, historicalAlgoDailyValues := backtestPortfolioOptimized(historicalPortfolioWithMAs, initialCapital)
	historicalSpyDailyValues := calculateBuyAndHold(spyHistoricalDF, initialCapital)
	fmt.Println("Historical backtest complete.")

	// 3. Create and prepare the output CSV file for streaming
	if err := os.MkdirAll(filepath.Dir(outputFile), 0755); err != nil {
		log.Fatalf("Failed to create output directory: %v", err)
	}
	outputF, err := os.Create(outputFile)
	if err != nil {
		log.Fatalf("Failed to create output file: %v", err)
	}
	defer outputF.Close()

	csvWriter := csv.NewWriter(outputF)
	header := []string{"Date", "Algorithm_Value", "SPY_Value", "Historical_SPY_Value", "Historical_Algo_Value", "Sim_ID"}
	if err := csvWriter.Write(header); err != nil {
		log.Fatalf("Failed to write CSV header: %v", err)
	}
	csvWriter.Flush()

	// 4. Implement Worker Pool for controlled concurrency
	var wg sync.WaitGroup
	var writerMutex sync.Mutex
	// numWorkers := runtime.NumCPU() // Use number of CPU cores to prevent crashing for large simulations
	numWorkers := numSimulations
	jobs := make(chan int, numSimulations)

	fmt.Printf("Starting %d Monte Carlo simulations using %d workers...\n", numSimulations, numWorkers)

	// Start worker goroutines
	for w := 1; w <= numWorkers; w++ {
		wg.Add(1)
		go worker(w, jobs, &wg, portfolioHistoricalData, historicalAlgoDailyValues, historicalSpyDailyValues, marketCaps, csvWriter, &writerMutex)
	}

	// Send jobs to the workers
	for j := 1; j <= numSimulations; j++ {
		jobs <- j
	}
	close(jobs)

	wg.Wait()

	fmt.Printf("\nSuccessfully completed all simulations.\n")
	fmt.Printf("Output data saved to '%s'\n", outputFile)
	fmt.Printf("Total execution time: %s\n", time.Since(startTime))
}

// worker function for the worker pool pattern
func worker(id int, jobs <-chan int, wg *sync.WaitGroup, historicalData map[string]dataframe.DataFrame, historicalAlgoDailyValues map[time.Time]float64, historicalSpyDailyValues map[time.Time]float64, marketCaps map[string]float64, writer *csv.Writer, mutex *sync.Mutex) {
	defer wg.Done()
	for simID := range jobs {
		runSingleSimulation(simID, historicalData, historicalAlgoDailyValues, historicalSpyDailyValues, marketCaps, writer, mutex)
	}
}

// --- Core Simulation Logic ---

func runSingleSimulation(simID int, historicalData map[string]dataframe.DataFrame, historicalAlgoDailyValues map[time.Time]float64, historicalSpyDailyValues map[time.Time]float64, marketCaps map[string]float64, writer *csv.Writer, mutex *sync.Mutex) {
	// Generate synthetic data for the portfolio tickers using bootstrapping
	fmt.Printf("Simulation %d: Generating synthetic data...\n", simID)
	syntheticPortfolio := generateSyntheticPortfolio(historicalData)

	// Create the synthetic SPY benchmark using a market-cap weighted average of the synthetic portfolio
	fmt.Printf("Simulation %d: Creating synthetic SPY benchmark...\n", simID)
	syntheticSPY := createWeightedSyntheticSPY(syntheticPortfolio, marketCaps)

	// Pre-calculate moving averages for the synthetic portfolio
	fmt.Printf("Simulation %d: Pre-calculating moving averages...\n", simID)
	portfolioWithMAs := precalculateAllMovingAverages(syntheticPortfolio)

	// Run the algorithm on the synthetic portfolio
	fmt.Printf("Simulation %d: Running backtest on synthetic data...\n", simID)
	_, algoDailyValues := backtestPortfolioOptimized(portfolioWithMAs, initialCapital)
	// Calculate Buy-and-Hold for the synthetic SPY benchmark
	fmt.Printf("Simulation %d: Calculating Buy-and-Hold for synthetic SPY...\n", simID)
	syntheticSpyDailyValues := calculateBuyAndHold(syntheticSPY, initialCapital)

	// Prepare results for this simulation
	fmt.Printf("Simulation %d: Preparing results for output...\n", simID)
	var simResults [][]string
	// Use the dates from the historical run as the master timeline
	dates := getSortedDates(historicalAlgoDailyValues)
	for _, date := range dates {
		record := []string{
			date.Format("2006-01-02"),
			strconv.FormatFloat(algoDailyValues[date], 'f', 2, 64),
			strconv.FormatFloat(syntheticSpyDailyValues[date], 'f', 2, 64),
			strconv.FormatFloat(historicalSpyDailyValues[date], 'f', 2, 64),
			strconv.FormatFloat(historicalAlgoDailyValues[date], 'f', 2, 64),
			strconv.Itoa(simID),
		}
		simResults = append(simResults, record)
	}

	// Lock the mutex, write all results for this sim, then unlock
	mutex.Lock()
	writer.WriteAll(simResults)
	writer.Flush() // Ensure data is written to the file
	mutex.Unlock()
}

// --- Data Generation ---

func generateSyntheticPortfolio(historicalData map[string]dataframe.DataFrame) map[string]dataframe.DataFrame {
	syntheticPortfolio := make(map[string]dataframe.DataFrame)
	for ticker, df := range historicalData {
		// Use block bootstrapping for more realistic simulations
		syntheticPortfolio[ticker] = generateBlockBootstrapData(df)
	}
	return syntheticPortfolio
}

// generateBlockBootstrapData creates a new price series by randomly sampling blocks of historical log returns.
func generateBlockBootstrapData(historicalDf dataframe.DataFrame) dataframe.DataFrame {
	closePrices := historicalDf.Col("CLOSE").Float()
	logReturnsSeries := historicalDf.Col("LOG_RETURNS")
	dates := historicalDf.Col("DATE").Records()
	numDays := len(dates)

	if logReturnsSeries.Err != nil {
		fmt.Printf("Warning: 'LOG_RETURNS' column not found for a ticker. Falling back to flat prices.\n")
		return historicalDf.Mutate(series.New(closePrices, series.Float, "OPEN")).
			Mutate(series.New(closePrices, series.Float, "HIGH")).
			Mutate(series.New(closePrices, series.Float, "LOW"))
	}

	// Create a pool of historical log returns, skipping NaN values
	var validReturns []float64
	for i := 0; i < logReturnsSeries.Len(); i++ {
		val := logReturnsSeries.Elem(i).Float()
		if !math.IsNaN(val) {
			validReturns = append(validReturns, val)
		}
	}

	if len(validReturns) < blockSize {
		fmt.Printf("Warning: Not enough valid returns to perform block bootstrap. Falling back to flat prices.\n")
		return historicalDf.Mutate(series.New(closePrices, series.Float, "OPEN")).
			Mutate(series.New(closePrices, series.Float, "HIGH")).
			Mutate(series.New(closePrices, series.Float, "LOW"))
	}

	// Create overlapping blocks of returns
	var blocks [][]float64
	for i := 0; i <= len(validReturns)-blockSize; i++ {
		blocks = append(blocks, validReturns[i:i+blockSize])
	}

	firstPrice := closePrices[0]
	prices := make([]float64, numDays)
	if numDays > 0 {
		prices[0] = firstPrice
	}

	// Build the new price path by stringing together random blocks of returns
	currentDay := 1
	for currentDay < numDays {
		randomBlock := blocks[rand.Intn(len(blocks))]
		for _, dailyReturn := range randomBlock {
			if currentDay >= numDays {
				break
			}
			prices[currentDay] = prices[currentDay-1] * math.Exp(dailyReturn)
			currentDay++
		}
	}

	return dataframe.New(
		series.New(dates, series.String, "DATE"),
		series.New(prices, series.Float, "OPEN"),
		series.New(prices, series.Float, "HIGH"),
		series.New(prices, series.Float, "LOW"),
		series.New(prices, series.Float, "CLOSE"),
	)
}

// createWeightedSyntheticSPY generates a market-cap weighted benchmark using provided market caps.
func createWeightedSyntheticSPY(syntheticPortfolio map[string]dataframe.DataFrame, marketCaps map[string]float64) dataframe.DataFrame {
	if len(syntheticPortfolio) == 0 {
		return dataframe.DataFrame{}
	}

	// 1. Calculate weights based on the provided market caps
	tickerWeights := make(map[string]float64)
	totalMarketCap := 0.0
	for ticker := range syntheticPortfolio {
		if cap, ok := marketCaps[ticker]; ok {
			totalMarketCap += cap
		}
	}

	if totalMarketCap > 0 {
		for ticker := range syntheticPortfolio {
			if cap, ok := marketCaps[ticker]; ok {
				tickerWeights[ticker] = cap / totalMarketCap
			}
		}
	}

	// 2. Apply weights to the synthetic data to create the index
	var numRows int
	var firstTicker string
	for ticker, df := range syntheticPortfolio {
		if firstTicker == "" {
			numRows = df.Nrow()
			firstTicker = ticker
		}
	}

	weightedAvgPrices := make([]float64, numRows)
	dates := syntheticPortfolio[firstTicker].Col("DATE").Records()

	for i := 0; i < numRows; i++ {
		dailyWeightedSum := 0.0
		for ticker, df := range syntheticPortfolio {
			if weight, ok := tickerWeights[ticker]; ok && i < df.Nrow() {
				price := df.Col("CLOSE").Elem(i).Float()
				dailyWeightedSum += price * weight
			}
		}
		weightedAvgPrices[i] = dailyWeightedSum
	}

	return dataframe.New(
		series.New(dates, series.String, "DATE"),
		series.New(weightedAvgPrices, series.Float, "OPEN"),
		series.New(weightedAvgPrices, series.Float, "HIGH"),
		series.New(weightedAvgPrices, series.Float, "LOW"),
		series.New(weightedAvgPrices, series.Float, "CLOSE"),
	)
}

// --- Backtesting & Benchmarking ---

func calculateBuyAndHold(spyDF dataframe.DataFrame, initialCapital float64) map[time.Time]float64 {
	dailyValues := make(map[time.Time]float64)
	prices := spyDF.Col("CLOSE").Float()
	datesStr := spyDF.Col("DATE").Records()

	if len(prices) == 0 {
		return dailyValues
	}

	firstPrice := 0.0
	firstPriceIndex := -1
	for i, p := range prices {
		if p > 0 {
			firstPrice = p
			firstPriceIndex = i
			break
		}
	}

	if firstPriceIndex == -1 {
		return dailyValues // No valid starting price found
	}

	sharesToBuy := initialCapital / firstPrice

	for i := 0; i < len(prices); i++ {
		date, err := time.Parse("2006-01-02", datesStr[i])
		if err != nil {
			continue
		}
		if i < firstPriceIndex {
			dailyValues[date] = initialCapital // Value is just capital before the first price
		} else {
			currentValue := sharesToBuy * prices[i]
			dailyValues[date] = currentValue
		}
	}
	return dailyValues
}

func backtestPortfolioOptimized(dataframes map[string]dataframe.DataFrame, initialCapital float64) ([]Trade, map[time.Time]float64) {
	tradeEventChan := make(chan []Trade, len(dataframes))
	var wg sync.WaitGroup

	for ticker, df := range dataframes {
		wg.Add(1)
		go func(ticker string, df dataframe.DataFrame) {
			defer wg.Done()
			var events []Trade
			datesStr := df.Col("DATE").Records()
			maShort := df.Col(fmt.Sprintf("MA_%d", shortMALength)).Float()
			maLong := df.Col(fmt.Sprintf("MA_%d", longMALength)).Float()
			openPrices := df.Col("OPEN").Float()

			inTrade := false
			for i := 1; i < df.Nrow(); i++ {
				currentDate, _ := time.Parse("2006-01-02", datesStr[i])

				if maShort[i] > maLong[i] && maShort[i-1] <= maLong[i-1] && !inTrade {
					entryTrade := Trade{Ticker: ticker, EntryDate: currentDate, EntryPrice: openPrices[i]}
					events = append(events, entryTrade)
					inTrade = true
				}

				if maShort[i] < maLong[i] && maShort[i-1] >= maLong[i-1] && inTrade {
					exitTrade := Trade{Ticker: ticker, ExitDate: currentDate, ExitPrice: openPrices[i]}
					events = append(events, exitTrade)
					inTrade = false
				}
			}
			tradeEventChan <- events
		}(ticker, df)
	}

	wg.Wait()
	close(tradeEventChan)

	allTradeEvents := make(map[time.Time][]Trade)
	dateSet := make(map[time.Time]struct{})
	for eventSlice := range tradeEventChan {
		for _, event := range eventSlice {
			var eventDate time.Time
			if !event.EntryDate.IsZero() {
				eventDate = event.EntryDate
			} else {
				eventDate = event.ExitDate
			}
			allTradeEvents[eventDate] = append(allTradeEvents[eventDate], event)
			dateSet[eventDate] = struct{}{}
		}
	}

	for _, df := range dataframes {
		for _, dateStr := range df.Col("DATE").Records() {
			date, err := time.Parse("2006-01-02", dateStr)
			if err == nil {
				dateSet[date] = struct{}{}
			}
		}
	}

	sortedDates := getSortedDatesFromSet(dateSet)
	dailyValues := make(map[time.Time]float64)
	openPositions := make(map[string]*Trade)
	currentCapital := initialCapital
	finalTrades := []Trade{}
	dailyRiskFreeRate := math.Pow(1+riskFreeRate, 1.0/365.0) - 1

	for _, date := range sortedDates {
		// Accrue interest on cash held
		currentCapital *= (1 + dailyRiskFreeRate)

		if tradesForDay, found := allTradeEvents[date]; found {
			for _, event := range tradesForDay {
				if !event.ExitDate.IsZero() {
					if openTrade, isOpen := openPositions[event.Ticker]; isOpen {
						currentCapital += openTrade.Shares * event.ExitPrice
						openTrade.ExitDate = event.ExitDate
						openTrade.ExitPrice = event.ExitPrice
						finalTrades = append(finalTrades, *openTrade)
						delete(openPositions, event.Ticker)
					}
				}
			}
			for _, event := range tradesForDay {
				if !event.EntryDate.IsZero() && event.ExitDate.IsZero() {
					if event.EntryPrice > 0 {
						positionValue := currentCapital * perTradeRisk
						shares := positionValue / event.EntryPrice
						if currentCapital >= positionValue && shares > 0 {
							currentCapital -= positionValue
							event.Shares = shares
							openPositions[event.Ticker] = &event
						}
					}
				}
			}
		}

		openPositionValue := 0.0
		for ticker, trade := range openPositions {
			priceToday := getPriceForDate(dataframes[ticker], date, "OPEN")
			if priceToday > 0 {
				openPositionValue += trade.Shares * priceToday
			} else {
				openPositionValue += trade.Shares * trade.EntryPrice
			}
		}
		dailyValues[date] = currentCapital + openPositionValue
	}

	return finalTrades, dailyValues
}

// --- Data Processing & Helpers ---

func loadHistoricalData(dir string) (map[string]dataframe.DataFrame, error) {
	data := make(map[string]dataframe.DataFrame)
	files, err := ioutil.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("could not read directory %s: %w", dir, err)
	}

	for _, file := range files {
		if !file.IsDir() && strings.HasSuffix(file.Name(), "_yahoo_finance.csv") {
			filePath := filepath.Join(dir, file.Name())
			f, err := os.Open(filePath)
			if err != nil {
				fmt.Printf("Warning: Could not open file %s: %v\n", filePath, err)
				continue
			}

			df := dataframe.ReadCSV(f)
			if df.Error() != nil {
				fmt.Printf("Warning: Could not read CSV %s: %v\n", filePath, df.Error())
				f.Close()
				continue
			}
			f.Close()
			ticker := strings.TrimSuffix(file.Name(), "_yahoo_finance.csv")
			data[ticker] = df
		}
	}
	return data, nil
}

// loadMarketCaps reads the market cap data from the specified CSV file.
func loadMarketCaps(filePath string) (map[string]float64, error) {
	caps := make(map[string]float64)
	f, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("could not open market caps file %s: %w", filePath, err)
	}
	defer f.Close()

	reader := csv.NewReader(f)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("could not read market caps csv: %w", err)
	}

	// Skip header row (i=0)
	for i, record := range records {
		if i == 0 {
			continue
		}
		ticker := record[0]
		marketCap, err := strconv.ParseFloat(record[1], 64)
		if err != nil {
			fmt.Printf("Warning: Could not parse market cap for %s: %v\n", ticker, err)
			continue
		}
		caps[ticker] = marketCap
	}
	return caps, nil
}


func precalculateAllMovingAverages(dataframes map[string]dataframe.DataFrame) map[string]dataframe.DataFrame {
	processed := make(map[string]dataframe.DataFrame)
	for ticker, df := range dataframes {
		processed[ticker] = precalculateMovingAverages(df, "CLOSE")
	}
	return processed
}

func precalculateMovingAverages(df dataframe.DataFrame, priceCol string) dataframe.DataFrame {
	prices := df.Col(priceCol).Float()
	shortMAs := calculateSimpleMA(prices, shortMALength)
	longMAs := calculateSimpleMA(prices, longMALength)

	maShortSeries := series.New(shortMAs, series.Float, fmt.Sprintf("MA_%d", shortMALength))
	maLongSeries := series.New(longMAs, series.Float, fmt.Sprintf("MA_%d", longMALength))

	return df.Mutate(maShortSeries).Mutate(maLongSeries)
}

func calculateSimpleMA(prices []float64, window int) []float64 {
	if len(prices) < window {
		return make([]float64, len(prices))
	}
	ma := make([]float64, len(prices))
	sum := 0.0
	for i := 0; i < len(prices); i++ {
		sum += prices[i]
		if i >= window {
			sum -= prices[i-window]
		}
		if i >= window-1 {
			ma[i] = sum / float64(window)
		}
	}
	return ma
}

// --- Math & Utility Functions ---

func mean(data []float64) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range data {
		sum += v
	}
	return sum / float64(len(data))
}

func stdDev(data []float64, mean float64) float64 {
	if len(data) == 0 {
		return 0
	}
	sumOfSquares := 0.0
	for _, v := range data {
		sumOfSquares += math.Pow(v-mean, 2)
	}
	return math.Sqrt(sumOfSquares / float64(len(data)))
}

func getSortedDates(dailyValues map[time.Time]float64) []time.Time {
	var dates []time.Time
	for date := range dailyValues {
		dates = append(dates, date)
	}
	sort.Slice(dates, func(i, j int) bool {
		return dates[i].Before(dates[j])
	})
	return dates
}

func getSortedDatesFromSet(dateSet map[time.Time]struct{}) []time.Time {
	var dates []time.Time
	for date := range dateSet {
		dates = append(dates, date)
	}
	sort.Slice(dates, func(i, j int) bool {
		return dates[i].Before(dates[j])
	})
	return dates
}

func getPriceForDate(df dataframe.DataFrame, date time.Time, colName string) float64 {
	subset := df.Filter(dataframe.F{
		Colname:    "DATE",
		Comparator: series.Eq,
		Comparando: date.Format("2006-01-02"),
	})
	if subset.Nrow() > 0 {
		price := subset.Col(colName).Elem(0).Float()
		if subset.Col(colName).Err == nil {
			return price
		}
	}
	return 0
}
