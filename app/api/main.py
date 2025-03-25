from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
import asyncio
import logging
import time
from datetime import datetime, timedelta
from openchart import NSEData
from .configs import ALL_STOCKS, STOCK_CATEGORIES, MARKET_CAP_CATEGORIES, BUSINESS_CATEGORIES, CACHE_EXPIRY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="52-Week Dash", description="Nifty 200 Stock Tracker API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize NSE data client and download data
nse = NSEData()
nse.download()  # Download required data first

# Cache for storing stock data
CACHE = {
    "stock_data": {},
    "last_updated": None
}

def convert_numpy_types(obj):
    """Convert numpy types to Python native types."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    return obj

async def get_stock_data(symbol: str) -> Dict[str, Any]:
    """Get stock data for a given symbol."""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Get historical data
        hist_data = nse.historical(
            symbol=symbol,
            exchange="NSE",
            start=start_date,
            end=end_date,
            interval="1d"
        )
        
        if hist_data is None or hist_data.empty:
            raise Exception(f"No data available for {symbol}")
        
        # Ensure column names are lowercase
        hist_data.columns = hist_data.columns.str.lower()
        
        # Check required columns
        required_columns = ["high", "low", "close"]
        if not all(col in hist_data.columns for col in required_columns):
            raise Exception(f"Missing required columns for {symbol}")
        
        # Calculate metrics
        current_price = float(hist_data["close"].iloc[-1])
        week_52_high = float(hist_data["high"].max())
        week_52_low = float(hist_data["low"].min())
        
        # Calculate percentages
        pct_from_high = float(((current_price - week_52_high) / week_52_high) * 100)
        pct_from_low = float(((current_price - week_52_low) / week_52_low) * 100)
        
        # Get additional info if available
        company_info = nse.info(symbol) if hasattr(nse, 'info') else {}
        
        # Create response data with explicit type conversion
        response_data = {
            "symbol": symbol,
            "company_name": company_info.get('companyName', symbol),
            "current_price": round(current_price, 2),
            "week_52_high": round(week_52_high, 2),
            "week_52_low": round(week_52_low, 2),
            "pct_from_high": round(pct_from_high, 2),
            "pct_from_low": round(pct_from_low, 2),
            "currency": "INR",
            "volume": int(hist_data["volume"].iloc[-1]) if "volume" in hist_data.columns else None,
            "avg_volume": float(hist_data["volume"].mean()) if "volume" in hist_data.columns else None,
            "sector": company_info.get('sector', None),
            "industry": company_info.get('industry', None)
        }
        
        # Convert any remaining numpy types
        return convert_numpy_types(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "error": str(e)
        }

async def fetch_stocks_batch(stocks: List[str], batch_size: int = 10) -> List[Dict[str, Any]]:
    """Fetch data for a batch of stocks with rate limiting."""
    results = []
    for i in range(0, len(stocks), batch_size):
        batch = stocks[i:i + batch_size]
        tasks = [get_stock_data(symbol) for symbol in batch]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
        # Add delay between batches to avoid rate limiting
        if i + batch_size < len(stocks):
            await asyncio.sleep(0.5)
    return results

@app.get("/api/stocks", response_model=List[Dict[str, Any]])
async def get_all_stocks():
    """Get data for all stocks."""
    global CACHE
    
    try:
        current_time = time.time()
        
        # Check if cache needs refresh
        if (CACHE["last_updated"] is None or 
            current_time - CACHE["last_updated"] > CACHE_EXPIRY):
            
            logger.info("Refreshing stock data...")
            all_stocks_data = await fetch_stocks_batch(ALL_STOCKS)
            
            # Filter out stocks with errors
            valid_stocks = [stock for stock in all_stocks_data if "error" not in stock]
            
            # Update cache
            CACHE["stock_data"] = {stock["symbol"]: stock for stock in valid_stocks}
            CACHE["last_updated"] = current_time
            
            return valid_stocks
        
        # Return cached data
        return list(CACHE["stock_data"].values())
        
    except Exception as e:
        logger.error(f"Error in get_all_stocks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{symbol}", response_model=Dict[str, Any])
async def get_stock(symbol: str):
    """Get detailed data for a specific stock."""
    try:
        # Check cache first
        if (CACHE["last_updated"] and 
            time.time() - CACHE["last_updated"] <= CACHE_EXPIRY and
            symbol in CACHE["stock_data"]):
            return CACHE["stock_data"][symbol]
        
        # Fetch fresh data
        stock_data = await get_stock_data(symbol)
        
        # Update cache if no error
        if "error" not in stock_data:
            CACHE["stock_data"][symbol] = stock_data
        
        return stock_data
        
    except Exception as e:
        logger.error(f"Error in get_stock for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add new endpoints for category types
@app.get("/api/category-types")
async def get_category_types():
    """Get available category types."""
    return {
        "types": [
            {
                "id": "market-cap",
                "name": "🏆 Market Cap Based",
                "description": "Stocks categorized by market capitalization"
            },
            {
                "id": "business",
                "name": "🏢 Business Groups",
                "description": "Stocks grouped by business conglomerates"
            }
        ]
    }

@app.get("/api/categories/market-cap", response_model=Dict[str, List[str]])
async def get_market_cap_categories():
    """Get market cap based categories."""
    return MARKET_CAP_CATEGORIES

@app.get("/api/categories/business", response_model=Dict[str, List[str]])
async def get_business_categories():
    """Get business group based categories."""
    return BUSINESS_CATEGORIES

@app.get("/api/categories/{category_type}/{category}", response_model=List[Dict[str, Any]])
async def get_category_stocks(category_type: str, category: str):
    """Get stocks for a specific category and type."""
    categories = MARKET_CAP_CATEGORIES if category_type == "market-cap" else BUSINESS_CATEGORIES
    
    if category not in categories:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found in {category_type}")
    
    try:
        current_time = time.time()
        
        # Check if cache needs refresh
        if (CACHE["last_updated"] is None or 
            current_time - CACHE["last_updated"] > CACHE_EXPIRY):
            await get_all_stocks()  # This will refresh the cache
        
        # Get stocks for the category
        category_stocks = categories[category]
        return [
            stock_data for stock_data in CACHE["stock_data"].values()
            if stock_data["symbol"] in category_stocks
        ]
    
    except Exception as e:
        logger.error(f"Error in get_category_stocks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files for frontend
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path / "public")), name="static")

@app.get("/", response_class=FileResponse)
async def read_index():
    """Serve the index.html file."""
    return FileResponse(str(frontend_path / "public" / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True) 