"""
Top 300 Most Popular/Liquid Tickers for Options Trading
Curated from: Top Market Cap, Highest Options Volume, Most Active Trading
"""

# ============================================================================
# TOP 100 MOST LIQUID OPTIONS TICKERS (Ranked by Average Daily Options Volume)
# ============================================================================
# This list prioritizes tickers with the highest options trading volume and
# open interest, ensuring maximum liquidity for options analysis.
# Index options use $ prefix (e.g. $SPX, $NDX, $RUT)
# ============================================================================

TOP_100_LIQUID_OPTIONS = [
    # Tier 1: Ultra-High Liquidity (500K+ contracts/day)
    '$SPX',   # S&P 500 Index Options (use $SPX for Schwab API)
    'SPY',    # S&P 500 ETF - #1 Most liquid ETF options
    'QQQ',    # Nasdaq 100 ETF - #2 Most liquid
    'AAPL',   # Apple
    'TSLA',   # Tesla
    'NVDA',   # NVIDIA
    'AMD',    # Advanced Micro Devices
    'MSFT',   # Microsoft
    'META',   # Meta Platforms
    'GOOGL',  # Alphabet
    'AMZN',   # Amazon
    
    # Tier 1 continued: Major ETFs & High-Volume Stocks
    'IWM',    # Russell 2000 ETF
    'GLD',    # Gold ETF
    'SLV',    # Silver ETF
    'XLE',    # Energy Sector ETF
    'XLF',    # Financial Sector ETF
    'NFLX',   # Netflix
    'DIS',    # Disney
    'COIN',   # Coinbase
    'PLTR',   # Palantir
    'SOFI',   # SoFi Technologies
    
    # Tier 2: Very High Liquidity (100K-500K contracts/day)
    'BA',     # Boeing
    'F',      # Ford
    'GME',    # GameStop
    'AMC',    # AMC Entertainment
    'NIO',    # NIO Inc
    'LCID',   # Lucid Motors
    'RIVN',   # Rivian
    'MARA',   # Marathon Digital
    'RIOT',   # Riot Platforms
    'SQ',     # Block (Square)
    'PYPL',   # PayPal
    'SNAP',   # Snap Inc
    'UBER',   # Uber
    'LYFT',   # Lyft
    'DASH',   # DoorDash
    'C',      # Citigroup
    'BAC',    # Bank of America
    'JPM',    # JPMorgan Chase
    'GS',     # Goldman Sachs
    'WFC',    # Wells Fargo
    'INTC',   # Intel
    'MU',     # Micron
    'QCOM',   # Qualcomm
    'AVGO',   # Broadcom
    'CRM',    # Salesforce
    'ORCL',   # Oracle
    'ADBE',   # Adobe
    'CSCO',   # Cisco
    'TXN',    # Texas Instruments
    'AMAT',   # Applied Materials
    
    # Tier 3: High Liquidity (50K-100K contracts/day)
    'XOM',    # Exxon Mobil
    'CVX',    # Chevron
    'PFE',    # Pfizer
    'JNJ',    # Johnson & Johnson
    'UNH',    # UnitedHealth
    'WMT',    # Walmart
    'HD',     # Home Depot
    'TGT',    # Target
    'COST',   # Costco
    'NKE',    # Nike
    'SBUX',   # Starbucks
    'MCD',    # McDonald's
    'GM',     # General Motors
    'BABA',   # Alibaba
    'JD',     # JD.com
    'PDD',    # Pinduoduo
    'MELI',   # MercadoLibre
    'V',      # Visa
    'MA',     # Mastercard
    'T',      # AT&T
    'VZ',     # Verizon
    'KO',     # Coca-Cola
    'PEP',    # PepsiCo
    'XLK',    # Technology Sector ETF
    'XLV',    # Healthcare Sector ETF
    'XLI',    # Industrial Sector ETF
    'GDX',    # Gold Miners ETF
    'SLB',    # Schlumberger
    'OXY',    # Occidental Petroleum
    'HAL',    # Halliburton
    
    # Tier 4: Good Liquidity (25K-50K contracts/day) - Leveraged & Volatility ETFs
    'ARKK',   # ARK Innovation ETF
    'SOXL',   # 3x Semiconductor Bull
    'TQQQ',   # 3x Nasdaq Bull
    'SQQQ',   # 3x Nasdaq Bear
    'SPXL',   # 3x S&P 500 Bull
    'TNA',    # 3x Small Cap Bull
    'TZA',    # 3x Small Cap Bear
    'UPRO',   # 3x S&P 500 Bull
    'UDOW',   # 3x Dow Bull
    'VXX',    # VIX Short-Term Futures
    'UVXY',   # 2x VIX Futures
    'EEM',    # Emerging Markets ETF
    'EWJ',    # Japan ETF
    'FXI',    # China Large-Cap ETF
    'EFA',    # EAFE ETF
    'VEA',    # FTSE Developed Markets
    'KWEB',   # China Internet ETF
    'SMH',    # Semiconductor ETF
    'XBI',    # Biotech ETF
    'IBB',    # Biotech ETF
]

# Major Indices & ETFs (20)
INDICES_ETFS = [
    '$SPX', 'SPY', 'QQQ', 'IWM', 'DIA',  # Major index ETFs
    'GLD', 'SLV', 'TLT', 'USO', 'UNG',   # Commodities
    'XLF', 'XLE', 'XLK', 'XLV', 'XLI',   # Sector ETFs
    'VXX', 'UVXY', 'SQQQ', 'TQQQ', 'SPXL' # Volatility & Leveraged
]

# Mega Cap Tech (30)
MEGA_CAP_TECH = [
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN',
    'META', 'NVDA', 'TSM', 'AVGO', 'ORCL',
    'ADBE', 'CRM', 'INTC', 'AMD', 'CSCO',
    'QCOM', 'TXN', 'AMAT', 'MU', 'LRCX',
    'KLAC', 'SNPS', 'CDNS', 'MRVL', 'ADI',
    'NXPI', 'ASML', 'SAP', 'SHOP', 'SQ'
]

# High Volume Growth/Meme Stocks (25)
GROWTH_MEME = [
    'TSLA', 'PLTR', 'SOFI', 'COIN', 'HOOD',
    'RBLX', 'SNAP', 'UBER', 'LYFT', 'DASH',
    'RIVN', 'LCID', 'NIO', 'XPEV', 'LI',
    'MARA', 'RIOT', 'COIN', 'GME', 'AMC',
    'BB', 'NOK', 'WISH', 'CLOV', 'ARKK'
]

# Streaming & Entertainment (15)
ENTERTAINMENT = [
    'NFLX', 'DIS', 'CMCSA', 'PARA', 'WBD',
    'SPOT', 'ROKU', 'DKNG', 'PENN', 'MGM',
    'LVS', 'WYNN', 'CZR', 'EA', 'TTWO'
]

# Finance (25)
FINANCE = [
    'JPM', 'BAC', 'WFC', 'C', 'GS',
    'MS', 'BLK', 'SCHW', 'AXP', 'USB',
    'PNC', 'TFC', 'COF', 'BK', 'STT',
    'V', 'MA', 'PYPL', 'SQ', 'AFRM',
    'SOFI', 'ALLY', 'BMO', 'TD', 'RY'
]

# Healthcare & Biotech (25)
HEALTHCARE = [
    'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK',
    'PFE', 'TMO', 'ABT', 'DHR', 'CVS',
    'BMY', 'AMGN', 'GILD', 'VRTX', 'REGN',
    'BIIB', 'MRNA', 'BNTX', 'ISRG', 'EW',
    'ZTS', 'DXCM', 'ILMN', 'ALGN', 'IDXX'
]

# Energy (20)
ENERGY = [
    'XOM', 'CVX', 'COP', 'SLB', 'EOG',
    'MPC', 'PSX', 'VLO', 'OXY', 'HAL',
    'DVN', 'FANG', 'HES', 'MRO', 'APA',
    'BP', 'SHEL', 'TTE', 'E', 'XLE'
]

# Consumer & Retail (25)
CONSUMER_RETAIL = [
    'WMT', 'HD', 'COST', 'LOW', 'TGT',
    'NKE', 'SBUX', 'MCD', 'BKNG', 'MAR',
    'GM', 'F', 'TSLA', 'TM', 'HMC',
    'LULU', 'ROST', 'TJX', 'DG', 'DLTR',
    'KR', 'SYY', 'HSY', 'GIS', 'K'
]

# Telecom & Media (15)
TELECOM_MEDIA = [
    'T', 'VZ', 'TMUS', 'CHTR', 'NFLX',
    'DIS', 'FOXA', 'FOX', 'VIAC', 'DISCA',
    'CMCSA', 'VIV', 'TEF', 'AMX', 'ORAN'
]

# Industrial & Aerospace (20)
INDUSTRIAL = [
    'BA', 'GE', 'CAT', 'DE', 'LMT',
    'RTX', 'HON', 'UNP', 'UPS', 'FDX',
    'NSC', 'CSX', 'GD', 'NOC', 'TXT',
    'PH', 'CMI', 'EMR', 'ETN', 'ITW'
]

# Real Estate & REITs (15)
REAL_ESTATE = [
    'AMT', 'PLD', 'CCI', 'EQIX', 'PSA',
    'SPG', 'O', 'WELL', 'DLR', 'AVB',
    'EQR', 'VTR', 'ARE', 'MAA', 'INVH'
]

# Semiconductor (20)
SEMICONDUCTOR = [
    'NVDA', 'AMD', 'INTC', 'AVGO', 'QCOM',
    'TXN', 'AMAT', 'MU', 'LRCX', 'KLAC',
    'MRVL', 'ADI', 'NXPI', 'MCHP', 'ON',
    'MPWR', 'SWKS', 'QRVO', 'WOLF', 'SLAB'
]

# Cloud & Software (25)
CLOUD_SOFTWARE = [
    'CRM', 'NOW', 'WDAY', 'TEAM', 'ZM',
    'SNOW', 'DDOG', 'NET', 'OKTA', 'CRWD',
    'ZS', 'PANW', 'FTNT', 'S', 'DOCU',
    'TWLO', 'PLTR', 'PATH', 'MDB', 'ESTC',
    'DT', 'NICE', 'VEEV', 'ADSK', 'INTU'
]

# Automotive & Transportation (15)
AUTOMOTIVE = [
    'TSLA', 'F', 'GM', 'TM', 'HMC',
    'RIVN', 'LCID', 'NIO', 'XPEV', 'LI',
    'UBER', 'LYFT', 'DASH', 'RACE', 'STLA'
]

# E-commerce & Payments (15)
ECOMMERCE = [
    'AMZN', 'BABA', 'JD', 'PDD', 'MELI',
    'SE', 'EBAY', 'ETSY', 'W', 'CHWY',
    'PYPL', 'SQ', 'V', 'MA', 'AFRM'
]

# Utilities (10)
UTILITIES = [
    'NEE', 'DUK', 'SO', 'D', 'AEP',
    'EXC', 'XEL', 'SRE', 'PEG', 'ED'
]


# High Volume Additions
HIGH_VOLUME = ['ABX', 'ACN', 'ACWI', 'ACWX', 'AEE', 'AGG', 'ALB', 'ALGM', 'AM', 'ANSS', 'ANY', 'APD', 'APTV', 'ASHR', 'ATGE', 'ATVI', 'AU', 'BAH', 'BAM', 'BCE', 'BF.B', 'BHP', 'BIGC', 'BITF', 'BKKT', 'BLNK', 'BMBL', 'BND', 'BNS', 'BTBT', 'BTI', 'BWA', 'BXP', 'CACI', 'CAG', 'CAN', 'CARV', 'CE', 'CEQP', 'CFG', 'CHL', 'CHPT', 'CHU', 'CI', 'CLSK', 'CM', 'CMA', 'CMS', 'CNP', 'COUR', 'CPB', 'CPNG', 'CPT', 'CTSH', 'DCP', 'DD', 'DELL', 'DEO', 'DHI', 'DIDI', 'DOW', 'DTE', 'DUST', 'EBON', 'ECL', 'EEM', 'EFA', 'EMN', 'ENLC', 'ENTG', 'EPD', 'ERX', 'ERY', 'ES', 'ESS', 'ET', 'ETR', 'EWJ', 'EWZ', 'FAS', 'FAZ', 'FCEL', 'FCX', 'FE', 'FITB', 'FMC', 'FXI', 'GDX', 'GDXJ', 'GEL', 'GOLD', 'GRAB', 'GREE', 'HBAN', 'HESM', 'HMLP', 'HOLX', 'HPQ', 'HSBC', 'HUT', 'HYG', 'IBM', 'IEF', 'IEMG', 'IFF', 'INDA', 'INFY', 'IXUS', 'JDST', 'JNK', 'JNUG', 'KBH', 'KBR', 'KEY', 'KMI', 'KO', 'KWEB', 'LABD', 'LABU', 'LDOS', 'LEA', 'LEN', 'LIN', 'LQD', 'MANT', 'MCHI', 'MDLZ', 'MFC', 'MHO', 'MKC', 'MLM', 'MMM', 'MMP', 'MPLX', 'MSTR', 'MTB', 'MTCH', 'MTH', 'MULN', 'NEM', 'NGL', 'NI', 'NILE', 'NTAP', 'NTRS', 'NUE', 'NUGT', 'NVR', 'NVS', 'OKE', 'OPEN', 'PAA', 'PAGP', 'PEP', 'PHI', 'PHM', 'PINS', 'PLUG', 'PODD', 'PPG', 'PPL', 'PSTG', 'RCI', 'RDS.A', 'RDS.B', 'RF', 'RIO', 'RPM', 'RS', 'RSX', 'SAIC', 'SHW', 'SHY', 'SID', 'SJM', 'SLF', 'SMCI', 'SMLP', 'SOS', 'SOXL', 'SPCE', 'SPDW', 'SPH', 'SPXS', 'STLD', 'STX', 'STZ', 'SVXY', 'TAP', 'TECH', 'TFX', 'TIP', 'TLK', 'TMHC', 'TNA', 'TOL', 'TU', 'TYL', 'TZA', 'U', 'UDOW', 'UDR', 'UL', 'UPRO', 'USAC', 'VALE', 'VAW', 'VCIT', 'VCR', 'VDC', 'VDE', 'VEA', 'VGT', 'VHT', 'VIS', 'VIX', 'VMC', 'VNO', 'VNQ', 'VOD', 'VOX', 'VPU', 'VWO', 'VXUS', 'WDC', 'WEC', 'WIT', 'WIX', 'WKEY', 'WMB', 'XIV', 'XLB', 'XLP', 'XLRE', 'XLU', 'XLY', 'XRAY', 'Z', 'ZION']

# Combine all lists
ALL_TICKERS = (
    HIGH_VOLUME +
    INDICES_ETFS +
    MEGA_CAP_TECH +
    GROWTH_MEME +
    ENTERTAINMENT +
    FINANCE +
    HEALTHCARE +
    ENERGY +
    CONSUMER_RETAIL +
    TELECOM_MEDIA +
    INDUSTRIAL +
    REAL_ESTATE +
    SEMICONDUCTOR +
    CLOUD_SOFTWARE +
    AUTOMOTIVE +
    ECOMMERCE +
    UTILITIES
)

# Remove duplicates and sort
ALL_TICKERS = sorted(list(set(ALL_TICKERS)))

# Categorization for dropdown grouping
TICKER_CATEGORIES = {
    'High Volume': HIGH_VOLUME,
    'Indices & ETFs': INDICES_ETFS,
    'Mega Cap Tech': MEGA_CAP_TECH,
    'Growth & Meme': GROWTH_MEME,
    'Entertainment': ENTERTAINMENT,
    'Finance': FINANCE,
    'Healthcare & Biotech': HEALTHCARE,
    'Energy': ENERGY,
    'Consumer & Retail': CONSUMER_RETAIL,
    'Telecom & Media': TELECOM_MEDIA,
    'Industrial & Aerospace': INDUSTRIAL,
    'Real Estate': REAL_ESTATE,
    'Semiconductor': SEMICONDUCTOR,
    'Cloud & Software': CLOUD_SOFTWARE,
    'Automotive': AUTOMOTIVE,
    'E-commerce': ECOMMERCE,
    'Utilities': UTILITIES,
}

# For easy access in other modules
if __name__ == "__main__":
    print(f"Total unique tickers: {len(ALL_TICKERS)}")
    print(f"Top 100 liquid options tickers: {len(TOP_100_LIQUID_OPTIONS)}")
