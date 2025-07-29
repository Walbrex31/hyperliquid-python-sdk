#!/usr/bin/env python3

import json
import time
import example_utils
from hyperliquid.utils import constants

def find_ueth_usdc_pair(info):
    """Find the correct asset identifier for UETH/USDC trading pair"""
    spot_meta = info.spot_meta()
    
    for asset_info in spot_meta["universe"]:
        name = asset_info["name"]
        tokens = asset_info["tokens"]
        base_token = spot_meta["tokens"][tokens[0]]
        quote_token = spot_meta["tokens"][tokens[1]]
        pair_name = f"{base_token['name']}/{quote_token['name']}"
        
        if pair_name == "UETH/USDC":
            return name, pair_name
    
    raise Exception("UETH/USDC trading pair not found!")

def get_balance(info, address, token_name):
    """Get current balance of a specific token"""
    spot_state = info.spot_user_state(address)
    for balance in spot_state["balances"]:
        if balance["coin"] == token_name:
            return float(balance["total"])
    return 0.0

def execute_single_roundtrip(exchange, info, address, ueth_asset, trade_num, total_trades):
    """Execute a single round-trip trade and return results"""
    print(f"\n🔄 TRADE #{trade_num}/{total_trades}")
    print("=" * 40)
    
    try:
        # Get current balances
        usdc_before = get_balance(info, address, "USDC")
        
        if usdc_before < 1:
            raise Exception(f"Insufficient USDC: ${usdc_before:.2f}")
        
        # Get current price and calculate trade amount
        all_mids = info.all_mids()
        ueth_price = float(all_mids[ueth_asset])
        estimated_ueth_amount = usdc_before / ueth_price
        
        # Round DOWN to 4 decimals to ensure we don't exceed USDC balance
        import math
        ueth_trade_amount = math.floor(estimated_ueth_amount * 10000) / 10000
        
        print(f"💰 Available: ${usdc_before:.2f} USDC")
        print(f"📈 UETH Price: ${ueth_price:.2f}")
        print(f"🎯 Trading: {ueth_trade_amount:.4f} UETH")
        
        # Step 1: Buy UETH
        print(f"🛒 Buying {ueth_trade_amount:.4f} UETH...")
        buy_result = exchange.market_open(
            name=ueth_asset,
            is_buy=True, 
            sz=ueth_trade_amount,
            slippage=0.001  # 0.1% slippage tolerance
        )
        
        if buy_result["status"] != "ok":
            raise Exception(f"Buy failed: {buy_result}")
        
        time.sleep(1)  # Faster execution
        
        # Step 2: Sell UETH
        print(f"💰 Selling {ueth_trade_amount:.4f} UETH...")
        sell_result = exchange.market_open(
            name=ueth_asset,
            is_buy=False,
            sz=ueth_trade_amount,
            slippage=0.001  # 0.1% slippage tolerance
        )
        
        if sell_result["status"] != "ok":
            raise Exception(f"Sell failed: {sell_result}")
        
        time.sleep(1)  # Faster execution
        
        # Calculate results
        usdc_after = get_balance(info, address, "USDC")
        trade_cost = usdc_before - usdc_after
        volume_generated = ueth_trade_amount * ueth_price * 2  # Buy + sell
        
        print(f"✅ Trade complete!")
        print(f"   Volume: ${volume_generated:.2f}")
        print(f"   Cost: ${trade_cost:.3f}")
        print(f"   Remaining: ${usdc_after:.2f} USDC")
        
        return {
            'success': True,
            'volume': volume_generated,
            'cost': trade_cost,
            'usdc_remaining': usdc_after,
            'ueth_amount': ueth_trade_amount,
            'ueth_price': ueth_price
        }
        
    except Exception as e:
        print(f"❌ Trade #{trade_num} failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'volume': 0,
            'cost': 0
        }

def main():
    """Execute 50 consecutive UETH/USDC round-trip trades"""
    
    print("=" * 60)
    print("🚀 UETH/USDC 50-TRADE VOLUME GENERATOR")
    print("=" * 60)
    print()
    
    try:
        # Setup connection
        print("🔗 Connecting to Hyperliquid mainnet...")
        address, info, exchange = example_utils.setup(base_url=constants.MAINNET_API_URL, skip_ws=True)
        print(f"✅ Connected! Account: {address}")
        
        # Find trading pair
        ueth_asset, pair_name = find_ueth_usdc_pair(info)
        print(f"✅ Found trading pair: {pair_name}")
        
        # Get initial balance
        initial_usdc = get_balance(info, address, "USDC")
        print(f"💰 Starting balance: ${initial_usdc:.2f} USDC")
        print()
        
        # Track cumulative stats
        total_volume = 0
        total_cost = 0
        successful_trades = 0
        failed_trades = 0
        trade_results = []
        total_trades = 50
        
        start_time = time.time()
        
        # Execute 50 trades
        for trade_num in range(1, total_trades + 1):
            result = execute_single_roundtrip(exchange, info, address, ueth_asset, trade_num, total_trades)
            trade_results.append(result)
            
            if result['success']:
                successful_trades += 1
                total_volume += result['volume']
                total_cost += result['cost']
                
                # Show progress every 10 trades
                if trade_num % 10 == 0:
                    progress_pct = (trade_num / total_trades) * 100
                    print(f"\n📊 Progress: {progress_pct:.0f}% ({trade_num}/{total_trades} trades)")
                    print(f"Volume so far: ${total_volume:.2f}")
                    print(f"Total cost so far: ${total_cost:.2f}")
            else:
                failed_trades += 1
                print(f"⚠️ Stopping due to trade failure...")
                break
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Final results
        final_usdc = get_balance(info, address, "USDC")
        
        print("\n" + "=" * 60)
        print("📊 FINAL RESULTS")
        print("=" * 60)
        print(f"⏱️ Execution time: {execution_time:.1f} seconds ({execution_time/60:.1f} minutes)")
        print(f"✅ Successful trades: {successful_trades}/50")
        print(f"❌ Failed trades: {failed_trades}/50")
        print()
        print(f"💰 Starting USDC: ${initial_usdc:.2f}")
        print(f"💰 Final USDC: ${final_usdc:.2f}")
        print(f"💸 Total cost: ${total_cost:.2f}")
        print()
        print(f"📈 Total volume generated: ${total_volume:.2f}")
        print(f"📊 Average volume per trade: ${total_volume/max(successful_trades,1):.2f}")
        print(f"💹 Cost per $1 volume: {(total_cost/max(total_volume,1))*100:.3f}%")
        print()
        
        if successful_trades > 0:
            print("💡 PROGRESS TOWARD $100K VOLUME:")
            remaining_volume = 100000 - total_volume
            progress_pct = (total_volume / 100000) * 100
            print(f"Current progress: {progress_pct:.1f}%")
            print(f"Remaining needed: ${remaining_volume:.2f}")
            
            if total_volume > 0:
                trades_needed = remaining_volume / (total_volume / successful_trades)
                print(f"Est. trades still needed: {trades_needed:.0f}")
        
        print("\n🎯 TRADE SUMMARY (First 10 & Last 10):")
        print("-" * 50)
        # Show first 10 trades
        for i in range(min(10, len(trade_results))):
            result = trade_results[i]
            if result['success']:
                print(f"Trade {i+1:2d}: ${result['volume']:6.2f} volume, ${result['cost']:5.3f} cost")
            else:
                print(f"Trade {i+1:2d}: FAILED - {result.get('error', 'Unknown error')}")
        
        # Show last 10 trades if we have more than 10
        if len(trade_results) > 10:
            print("...")
            start_idx = max(10, len(trade_results) - 10)
            for i in range(start_idx, len(trade_results)):
                result = trade_results[i]
                if result['success']:
                    print(f"Trade {i+1:2d}: ${result['volume']:6.2f} volume, ${result['cost']:5.3f} cost")
                else:
                    print(f"Trade {i+1:2d}: FAILED - {result.get('error', 'Unknown error')}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ SETUP FAILED!")
        print(f"Error: {str(e)}")
        print("=" * 60)

if __name__ == "__main__":
    main() 