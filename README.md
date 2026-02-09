# Options Heatmap Dashboard

Real-time options market maker exposure analysis dashboard with gamma, vega, and delta heatmaps.

## Features

- **Statistical Color Scaling**: Z-score based color mapping for meaningful visualization
- **Real-Time Data**: Auto-refreshes every 60 seconds during market hours
- **ATM Highlighting**: Golden border marks the at-the-money strike
- **Extreme Value Indicators**: Stars mark maximum positive/negative exposures
- **Interactive Heatmap**: Hover for detailed exposure and Greek values

## Dashboard Components

### Heatmap View
- Gamma Exposure (GEX) and Vega Exposure (VEX) visualization
- Color-coded cells based on statistical significance
- Empty cells for zero exposure
- ATM strike highlighting

### Data Fetching
- Schwab API integration
- 100+ liquid options tickers
- Automated market hours scheduling

## Quick Start

1. Configure Schwab API credentials in `.env`
2. Run `python continuous_fetcher.py` to start data collection
3. Open `unified_dashboard.html` in browser

## Color Scheme

**Positive Exposure:**
- Light green: Below average
- Dark green: Average
- Yellow/Orange: 2+ standard deviations (outliers)

**Negative Exposure:**
- Dark blue: Above average  
- Darker blue: Average
- Dark purple: 2+ standard deviations (outliers)

## Technologies

- Python (data fetching)
- JavaScript (heatmap visualization)
- Schwab Market Data API
- Statistical z-score normalization

## License

MIT
