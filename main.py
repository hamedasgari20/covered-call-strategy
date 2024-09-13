import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')


# ---------------------------
# Step 1: Define Black-Scholes Function
# ---------------------------
def black_scholes_call(S, K, T, r, sigma):
    """
    Calculate the Black-Scholes price for a European call option.

    Parameters:
    - S: Spot price of the underlying asset
    - K: Strike price of the option
    - T: Time to expiration in years
    - r: Risk-free interest rate (annualized)
    - sigma: Volatility of the underlying asset (annualized)

    Returns:
    - call_price: Theoretical price of the call option
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return call_price


# ---------------------------
# Step 2: Fetch Historical Data
# ---------------------------
# Parameters
symbol = 'SPY'
start_date = '2020-01-01'
end_date = '2023-09-30'

# Download historical data
data = yf.download(symbol, start=start_date, end=end_date)
data = data['Close']

# ---------------------------
# Step 3: Calculate Volatility
# ---------------------------
# Calculate daily returns
data_df = pd.DataFrame(data)
data_df.rename(columns={'Close': 'Price'}, inplace=True)
data_df['Returns'] = np.log(data_df['Price'] / data_df['Price'].shift(1))

# Calculate rolling volatility (annualized)
window_size = 30
data_df['Volatility'] = data_df['Returns'].rolling(window=window_size).std() * np.sqrt(252)
data_df.dropna(inplace=True)

# ---------------------------
# Step 4: Identify Option Selling Dates
# ---------------------------
# Get the first trading day of each month
monthly_dates = data_df.resample('MS').first().index

# ---------------------------
# Step 5: Simulate Covered Call Strategy
# ---------------------------
# Initialize variables
cash = 0
shares = 0
portfolio_value = []
dates = []
positions = []

risk_free_rate = 0.01  # 1% annual risk-free rate
shares_per_contract = 100  # Number of shares per option contract

for current_date in data_df.index:
    S = data_df.loc[current_date, 'Price']
    sigma = data_df.loc[current_date, 'Volatility']

    # Update portfolio value
    portfolio_val = cash + shares * S
    dates.append(current_date)
    portfolio_value.append(portfolio_val)

    # Check for option expiration
    positions_to_remove = []
    for pos in positions:
        if current_date >= pos['expiration_date']:
            K = pos['K']
            # Option is exercised if stock price > strike price
            if S > K:
                # Option is exercised; shares are called away
                cash += shares * K
                shares = 0
            # Option expires worthless; keep shares
            positions_to_remove.append(pos)
    # Remove expired positions
    for pos in positions_to_remove:
        positions.remove(pos)

    # On monthly dates, sell a new call option
    if current_date in monthly_dates:
        # Buy shares if not holding any
        if shares == 0:
            shares = shares_per_contract  # Buying shares equal to one contract
            cash -= shares * S
        # Sell call option
        T = 30 / 252  # 30 days to expiration
        K = S * 1.05  # Strike price 5% above current price
        call_premium = black_scholes_call(S, K, T, risk_free_rate, sigma) * shares_per_contract  # Total premium
        positions.append({
            'expiration_date': current_date + pd.Timedelta(days=30),
            'K': K
        })
        cash += call_premium

# ---------------------------
# Step 6: Prepare Results
# ---------------------------
# Create a DataFrame for portfolio value
portfolio_df = pd.DataFrame({'Date': dates, 'Portfolio Value': portfolio_value})
portfolio_df.set_index('Date', inplace=True)

# Calculate buy-and-hold portfolio value
initial_investment = shares_per_contract * data_df['Price'].iloc[0]
buy_and_hold_value = shares_per_contract * data_df['Price']

# ---------------------------
# Step 7: Visualize the Results
# ---------------------------
plt.figure(figsize=(14, 7))
plt.plot(portfolio_df.index, portfolio_df['Portfolio Value'], label='Covered Call Strategy')
plt.plot(buy_and_hold_value.index, buy_and_hold_value.values, label='Buy and Hold Strategy')
plt.title('Covered Call Strategy vs. Buy and Hold Strategy')
plt.xlabel('Date')
plt.ylabel('Portfolio Value ($)')
plt.legend()
plt.grid(True)
plt.show()

# ---------------------------
# Step 8: Performance Metrics
# ---------------------------
# Calculate total returns
covered_call_return = (portfolio_value[-1] - portfolio_value[0]) / portfolio_value[0]
buy_and_hold_return = (buy_and_hold_value.iloc[-1] - buy_and_hold_value.iloc[0]) / buy_and_hold_value.iloc[0]

print(f"Total Return of Covered Call Strategy: {covered_call_return * 100:.2f}%")
print(f"Total Return of Buy and Hold Strategy: {buy_and_hold_return * 100:.2f}%")

# Calculate annualized returns
days = (portfolio_df.index[-1] - portfolio_df.index[0]).days
years = days / 365.25

annualized_covered_call_return = (1 + covered_call_return) ** (1 / years) - 1
annualized_buy_and_hold_return = (1 + buy_and_hold_return) ** (1 / years) - 1

print(f"Annualized Return of Covered Call Strategy: {annualized_covered_call_return * 100:.2f}%")
print(f"Annualized Return of Buy and Hold Strategy: {annualized_buy_and_hold_return * 100:.2f}%")
