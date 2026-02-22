import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CACHE_DIR = Path("/app/cached_data")

class CacheService:
    """
    Service to cache expensive API calls and data for each ticker.
    Stores data in /app/cached_data/{ticker}/step_{n}.json
    """
    
    @staticmethod
    def get_ticker_dir(ticker: str) -> Path:
        """Get the cache directory for a ticker"""
        ticker_dir = CACHE_DIR / ticker.upper()
        ticker_dir.mkdir(parents=True, exist_ok=True)
        return ticker_dir
    
    @staticmethod
    def get_step_cache_path(ticker: str, step_number: int) -> Path:
        """Get the cache file path for a specific step"""
        ticker_dir = CacheService.get_ticker_dir(ticker)
        return ticker_dir / f"step_{step_number}.json"
    
    @staticmethod
    def has_cached_step(ticker: str, step_number: int) -> bool:
        """Check if cached data exists for a step"""
        cache_path = CacheService.get_step_cache_path(ticker, step_number)
        return cache_path.exists()
    
    @staticmethod
    def save_step_data(ticker: str, step_number: int, data: Dict[str, Any]) -> None:
        """Save step results to cache"""
        try:
            cache_path = CacheService.get_step_cache_path(ticker, step_number)
            
            cache_data = {
                'ticker': ticker,
                'step_number': step_number,
                'data': data,
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'cache_version': '1.0'
            }
            
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
            
            logger.info(f"✓ Cached step {step_number} data for {ticker}")
            
        except Exception as e:
            logger.error(f"Failed to cache step {step_number} for {ticker}: {str(e)}")
    
    @staticmethod
    def load_step_data(ticker: str, step_number: int) -> Optional[Dict[str, Any]]:
        """Load cached step data if available"""
        try:
            cache_path = CacheService.get_step_cache_path(ticker, step_number)
            
            if not cache_path.exists():
                return None
            
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            logger.info(f"✓ Loaded cached step {step_number} data for {ticker}")
            return cache_data.get('data')
            
        except Exception as e:
            logger.error(f"Failed to load cached step {step_number} for {ticker}: {str(e)}")
            return None
    
    @staticmethod
    def get_cache_status(ticker: str) -> Dict[str, Any]:
        """Get status of all cached steps for a ticker"""
        ticker_dir = CacheService.get_ticker_dir(ticker)
        
        status = {
            'ticker': ticker,
            'has_cache': ticker_dir.exists(),
            'cached_steps': [],
            'cache_dir': str(ticker_dir)
        }
        
        if ticker_dir.exists():
            for step_num in range(1, 9):
                cache_path = CacheService.get_step_cache_path(ticker, step_num)
                if cache_path.exists():
                    try:
                        with open(cache_path, 'r') as f:
                            cache_data = json.load(f)
                        
                        status['cached_steps'].append({
                            'step': step_num,
                            'cached_at': cache_data.get('cached_at'),
                            'size_kb': round(cache_path.stat().st_size / 1024, 2)
                        })
                    except:
                        pass
        
        return status
    
    @staticmethod
    def clear_ticker_cache(ticker: str) -> None:
        """Clear all cached data for a ticker"""
        ticker_dir = CacheService.get_ticker_dir(ticker)
        
        if ticker_dir.exists():
            for cache_file in ticker_dir.glob("*.json"):
                cache_file.unlink()
            logger.info(f"Cleared cache for {ticker}")
    
    @staticmethod
    def list_all_cached_tickers() -> list:
        """List all tickers with cached data"""
        if not CACHE_DIR.exists():
            return []
        
        tickers = []
        for ticker_dir in CACHE_DIR.iterdir():
            if ticker_dir.is_dir():
                cache_files = list(ticker_dir.glob("step_*.json"))
                if cache_files:
                    tickers.append({
                        'ticker': ticker_dir.name,
                        'cached_steps': len(cache_files),
                        'last_updated': max(f.stat().st_mtime for f in cache_files)
                    })
        
        return sorted(tickers, key=lambda x: x['last_updated'], reverse=True)
