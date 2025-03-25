# 52-Week Dash

A web application to track Nifty 200 stocks relative to their 52-week highs and lows. Built with FastAPI and OpenChart.

## Features

- Real-time stock data from NSE using OpenChart
- Track current prices, 52-week highs and lows
- Calculate percentage distance from highs and lows
- Modern, responsive UI with search and sorting capabilities
- Automatic data refresh every 5 minutes
- Data caching to prevent API rate limiting

## Requirements

- Python 3.8 or higher
- pip (Python package installer)

## Quick Start

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd 52-week-dash
   ```

2. Run the application:
   - On any platform: Run `python run.py`

The application will:
1. Install required dependencies
2. Start the FastAPI server
3. Open your browser to http://127.0.0.1:8000

## Manual Setup

If you prefer to set up manually:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the server:
   ```bash
   python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. Open http://127.0.0.1:8000 in your browser

## API Endpoints

- `GET /api/stocks`: Get data for all stocks
- `GET /api/stocks/{symbol}`: Get detailed data for a specific stock

