#!/usr/bin/env python3

import json
import os
import eth_account
from hyperliquid.info import Info
from hyperliquid.utils import constants

def main():
    """
    Simple connectivity test that doesn't require account balance.
    This verifies your private key and API connection are working.
    """
    
    print("=" * 50)
    print("HYPERLIQUID CONNECTIVITY TEST")
    print("=" * 50)
    print()
    
    try:
        # Load config
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path) as f:
            config = json.load(f)
        
        # Verify private key format
        secret_key = config["secret_key"]
        if not secret_key.startswith("0x"):
            raise Exception("Private key must start with '0x'")
        
        # Derive account from private key
        account = eth_account.Account.from_key(secret_key)
        address = config["account_address"] if config["account_address"] else account.address
        
        print("🔑 WALLET INFORMATION")
        print("-" * 30)
        print(f"Your account address: {address}")
        if address != account.address:
            print(f"Agent/API wallet address: {account.address}")
        print()
        
        # Test API connectivity
        print("🌐 API CONNECTIVITY TEST")
        print("-" * 30)
        print("Connecting to Hyperliquid mainnet...")
        
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Test public API endpoint (doesn't require account balance)
        print("Testing public API endpoints...")
        all_mids = info.all_mids()
        print(f"✅ Retrieved {len(all_mids)} market mid prices")
        
        # Test account-specific endpoints
        print("Testing account-specific endpoints...")
        user_state = info.user_state(address)
        spot_user_state = info.spot_user_state(address)
        
        margin_summary = user_state["marginSummary"]
        account_value = float(margin_summary["accountValue"])
        
        print(f"✅ Retrieved account data successfully")
        print(f"   Account Value: ${account_value:,.2f}")
        print(f"   Spot Balances: {len(spot_user_state['balances'])} tokens")
        
        # Display detailed spot balances
        print()
        print("💰 DETAILED SPOT BALANCES")
        print("-" * 30)
        if len(spot_user_state['balances']) > 0:
            for balance in spot_user_state['balances']:
                coin = balance['coin']
                total = float(balance['total'])
                held = float(balance['hold'])
                available = total - held  # Calculate available as total minus held
                entry_ntl = float(balance.get('entryNtl', '0'))
                
                print(f"{coin}:")
                print(f"  Total: {total:,.6f}")
                print(f"  Available: {available:,.6f}")
                print(f"  Held: {held:,.6f}")
                if entry_ntl != 0:
                    print(f"  Entry Value: ${entry_ntl:,.2f}")
                print()
        else:
            print("No spot balances found")
        
        # Display perpetual positions
        print("📈 PERPETUAL POSITIONS")
        print("-" * 30)
        positions = []
        for position in user_state["assetPositions"]:
            if float(position["position"]["szi"]) != 0:  # Only show non-zero positions
                positions.append(position["position"])
        
        if len(positions) > 0:
            for position in positions:
                asset = position["coin"]
                size = float(position["szi"])
                entry_px = float(position["entryPx"]) if position["entryPx"] else 0
                unrealized_pnl = float(position["unrealizedPnl"])
                side = "LONG" if size > 0 else "SHORT"
                
                print(f"{asset}: {side}")
                print(f"  Size: {abs(size):,.6f}")
                print(f"  Entry Price: ${entry_px:,.2f}")
                print(f"  Unrealized PnL: ${unrealized_pnl:,.2f}")
                print()
        else:
            print("No open positions")
        
        # Display open orders
        print("📝 OPEN ORDERS")
        print("-" * 30)
        try:
            open_orders = info.open_orders(address)
            if len(open_orders) > 0:
                for order in open_orders:
                    asset = order["coin"]
                    side = "BUY" if order["side"] == "B" else "SELL"
                    size = order["sz"]
                    price = order["limitPx"]
                    order_type = order.get("orderType", "Limit")
                    
                    print(f"{asset}: {side} {size} @ ${price}")
                    print(f"  Type: {order_type}")
                    print()
            else:
                print("No open orders")
        except Exception as e:
            print(f"Could not retrieve open orders: {e}")
        
        # Display trading volume and activity
        print("📊 TRADING VOLUME & ACTIVITY")
        print("-" * 30)
        try:
            # Get recent trading fills
            recent_fills = info.user_fills(address)
            
            # Get trading fees and volume data
            user_fees_data = info.user_fees(address)
            
            # Calculate recent trading statistics
            if len(recent_fills) > 0:
                # Get last 50 fills for recent activity
                recent_fills_sample = recent_fills[:50] if len(recent_fills) > 50 else recent_fills
                
                total_volume = 0.0
                total_trades = len(recent_fills)
                assets_traded = set()
                
                for fill in recent_fills_sample:
                    # Calculate volume (price * size)
                    volume = float(fill['px']) * float(fill['sz'])
                    total_volume += volume
                    assets_traded.add(fill['coin'])
                
                print(f"Total Trades (All Time): {total_trades:,}")
                print(f"Assets Traded: {len(assets_traded)} different coins")
                print(f"Recent Volume (Last {len(recent_fills_sample)} trades): ${total_volume:,.2f}")
                
                # Show most recent trades
                print("\n🔥 RECENT TRADES (Last 5):")
                for i, fill in enumerate(recent_fills[:5]):
                    asset = fill['coin']
                    side = fill['side']
                    size = float(fill['sz'])
                    price = float(fill['px'])
                    volume = price * size
                    # Convert timestamp to readable format
                    import datetime
                    trade_time = datetime.datetime.fromtimestamp(fill['time'] / 1000)
                    
                    print(f"  {i+1}. {asset} {side} {size} @ ${price:,.2f} (${volume:,.2f}) - {trade_time.strftime('%Y-%m-%d %H:%M')}")
                
            else:
                print("No trading history found")
            
            # Display daily volume data if available
            if 'dailyUserVlm' in user_fees_data and len(user_fees_data['dailyUserVlm']) > 0:
                print(f"\n📈 DAILY VOLUME (Last 7 days):")
                daily_volumes = user_fees_data['dailyUserVlm'][-7:]  # Last 7 days
                for day_data in daily_volumes:
                    date = day_data['date']
                    add_volume = float(day_data['userAdd'])
                    cross_volume = float(day_data['userCross'])
                    total_day_volume = add_volume + cross_volume
                    if total_day_volume > 0:
                        print(f"  {date}: ${total_day_volume:,.2f} (Add: ${add_volume:,.2f}, Cross: ${cross_volume:,.2f})")
            
            # Show current fee rates
            if 'userAddRate' in user_fees_data:
                add_rate = float(user_fees_data['userAddRate']) * 100
                cross_rate = float(user_fees_data['userCrossRate']) * 100
                print(f"\n💳 CURRENT FEE RATES:")
                print(f"  Maker (Add): {add_rate:.4f}%")
                print(f"  Taker (Cross): {cross_rate:.4f}%")
                
        except Exception as e:
            print(f"Could not retrieve trading data: {e}")
        
        print("=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("Your Hyperliquid setup is working correctly.")
        
        if account_value == 0 and len(spot_user_state['balances']) == 0:
            print()
            print("💡 NEXT STEPS:")
            print("Your account is empty. To start trading:")
            print("1. Visit https://app.hyperliquid.xyz")
            print(f"2. Deposit funds to: {address}")
            print("3. Then you can run trading examples!")
        else:
            print("Your account has funds - you're ready to trade!")
        print("=" * 50)
        
    except Exception as e:
        print()
        print("❌ TEST FAILED!")
        print("-" * 30)
        print(f"Error: {str(e)}")
        print()
        print("💡 Check your config.json file and try again.")
        print("=" * 50)

if __name__ == "__main__":
    main() 