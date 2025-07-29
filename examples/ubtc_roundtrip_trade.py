#!/usr/bin/env python3

import json
import time
import example_utils
from hyperliquid.utils import constants

def find_usde_usdc_pair(info):
    """Find the correct asset identifier for USDE/USDC trading pair"""
    spot_meta = info.spot_meta()
    
    print("🔍 Looking for USDE/USDC trading pair...")
    for asset_info in spot_meta["universe"]:
        name = asset_info["name"]
        tokens = asset_info["tokens"]
        base_token = spot_meta["tokens"][tokens[0]]
        quote_token = spot_meta["tokens"][tokens[1]]
        pair_name = f"{base_token['name']}/{quote_token['name']}"
        
        if pair_name == "USDE/USDC":
            print(f"✅ Found USDE/USDC pair: {name}")
            return name, pair_name
    
    raise Exception("USDE/USDC trading pair not found!")

def get_balance(info, address, token_name):
    """Get current balance of a specific token"""
    spot_state = info.spot_user_state(address)
    for balance in spot_state["balances"]:
        if balance["coin"] == token_name:
            return float(balance["total"])
    return 0.0

def wait_for_fill(info, address, timeout=10):
    """Wait for recent orders to fill and return updated balances"""
    print(f"⏳ Waiting {timeout}s for orders to fill...")
    time.sleep(timeout)
    
    # Get recent fills to verify trades
    recent_fills = info.user_fills(address)
    if recent_fills:
        latest_fill = recent_fills[0]
        print(f"✅ Latest fill: {latest_fill['coin']} {latest_fill['side']} {latest_fill['sz']} @ ${latest_fill['px']}")
    
    return recent_fills

def main():
    """
    Perform a single UBTC/USDC round-trip trade:
    1. Buy UBTC with USDC at market price
    2. Immediately sell all UBTC back to USDC at market price
    3. Calculate P&L and fees paid
    """
    
    print("=" * 60)
    print("USDE/USDC ROUND-TRIP TRADE SIMULATOR")
    print("=" * 60)
    print()
    
    try:
        # Setup connection to mainnet
        print("🔗 Connecting to Hyperliquid mainnet...")
        address, info, exchange = example_utils.setup(base_url=constants.MAINNET_API_URL, skip_ws=True)
        print(f"✅ Connected! Trading with account: {address}")
        print()
        
        # Find USDE/USDC trading pair
        usde_asset, pair_name = find_usde_usdc_pair(info)
        print()
        
        # Get current market price for USDE
        all_mids = info.all_mids()
        usde_price = float(all_mids[usde_asset])
        print(f"📈 Current USDE price: ${usde_price:,.4f}")
        print()
        
        # Get initial balances
        print("💰 INITIAL BALANCES")
        print("-" * 30)
        initial_usdc = get_balance(info, address, "USDC")
        initial_usde = get_balance(info, address, "USDE")
        print(f"USDC: {initial_usdc:,.6f}")
        print(f"USDE: {initial_usde:,.6f}")
        print()
        
        # Calculate trade size (use 100% of USDC for maximum volume)
        trade_usdc_amount = initial_usdc
        estimated_usde_amount = trade_usdc_amount / usde_price
        
        if trade_usdc_amount < 1:
            raise Exception(f"Insufficient USDC balance for trading. Need at least $1, have ${initial_usdc:.2f}")
        
        print(f"📊 TRADE PLAN")
        print("-" * 30)
        print(f"Using: ${trade_usdc_amount:.2f} USDC (100% of balance)")
        print(f"Estimated UBTC to buy: {estimated_ubtc_amount:.8f} UBTC")
        print(f"Max slippage: 0.1% (tight protection)")
        print()
        
        # Step 1: Buy UBTC with USDC (market order)
        print("🛒 STEP 1: BUYING UBTC")
        print("-" * 30)
        print(f"Placing market buy order for ~{estimated_ubtc_amount:.8f} UBTC...")
        
        buy_result = exchange.market_open(
            name=ubtc_asset,
            is_buy=True, 
            sz=estimated_ubtc_amount,
            slippage=0.001  # 0.1% slippage tolerance
        )
        
        print(f"Buy order result: {buy_result}")
        
        if buy_result["status"] != "ok":
            raise Exception(f"Buy order failed: {buy_result}")
        
        # Wait for buy order to fill
        wait_for_fill(info, address, 5)
        
        # Get balances after buy
        usdc_after_buy = get_balance(info, address, "USDC")
        ubtc_after_buy = get_balance(info, address, "UBTC")
        
        print(f"USDC after buy: {usdc_after_buy:,.6f}")
        print(f"UBTC after buy: {ubtc_after_buy:,.8f}")
        
        actual_ubtc_bought = ubtc_after_buy - initial_ubtc
        usdc_spent = initial_usdc - usdc_after_buy
        
        if actual_ubtc_bought <= 0:
            raise Exception("No UBTC was received from buy order!")
        
        print(f"✅ Actually bought: {actual_ubtc_bought:.8f} UBTC")
        print(f"✅ Actually spent: ${usdc_spent:.6f} USDC")
        print(f"✅ Effective buy price: ${usdc_spent/actual_ubtc_bought:.2f}")
        print()
        
        # Step 2: Sell all UBTC back to USDC (market order)
        print("💰 STEP 2: SELLING UBTC")
        print("-" * 30)
        print(f"Placing market sell order for {actual_ubtc_bought:.8f} UBTC...")
        
        sell_result = exchange.market_open(
            name=ubtc_asset,
            is_buy=False,
            sz=actual_ubtc_bought,
            slippage=0.001  # 0.1% slippage tolerance
        )
        
        print(f"Sell order result: {sell_result}")
        
        if sell_result["status"] != "ok":
            raise Exception(f"Sell order failed: {sell_result}")
        
        # Wait for sell order to fill  
        wait_for_fill(info, address, 5)
        
        # Get final balances
        final_usdc = get_balance(info, address, "USDC")
        final_ubtc = get_balance(info, address, "UBTC")
        
        print(f"USDC after sell: {final_usdc:,.6f}")
        print(f"UBTC after sell: {final_ubtc:,.8f}")
        
        usdc_received = final_usdc - usdc_after_buy
        ubtc_sold = ubtc_after_buy - final_ubtc
        
        print(f"✅ Actually sold: {ubtc_sold:.8f} UBTC")
        print(f"✅ Actually received: ${usdc_received:.6f} USDC")
        print(f"✅ Effective sell price: ${usdc_received/ubtc_sold:.2f}")
        print()
        
        # Calculate P&L and fees
        print("📊 TRADE SUMMARY")
        print("=" * 40)
        
        net_usdc_change = final_usdc - initial_usdc
        total_volume = usdc_spent + usdc_received
        
        print(f"Initial USDC: {initial_usdc:.6f}")
        print(f"Final USDC: {final_usdc:.6f}")
        print(f"Net P&L: ${net_usdc_change:.6f}")
        print(f"Total Volume: ${total_volume:.2f}")
        print()
        
        # Get fee data to estimate fees paid
        try:
            user_fees_data = info.user_fees(address)
            taker_fee_rate = float(user_fees_data['userCrossRate'])
            estimated_fees = total_volume * taker_fee_rate
            
            print(f"Taker Fee Rate: {taker_fee_rate*100:.3f}%")
            print(f"Estimated Fees Paid: ${estimated_fees:.6f}")
            print()
            
            # Calculate spread loss (P&L minus fees)
            spread_loss = -net_usdc_change - estimated_fees
            print(f"Estimated Spread Loss: ${spread_loss:.6f}")
            print(f"Total Cost (Fees + Spread): ${-net_usdc_change:.6f}")
            
        except Exception as e:
            print(f"Could not calculate fees: {e}")
        
        print()
        print("=" * 60)
        print("✅ ROUND-TRIP TRADE COMPLETED!")
        print(f"Volume Generated: ${total_volume:.2f}")
        print(f"Net Cost: ${-net_usdc_change:.6f}")
        print("=" * 60)
        
    except Exception as e:
        print()
        print("❌ TRADE FAILED!")
        print("-" * 40)
        print(f"Error: {str(e)}")
        print()
        print("💡 Make sure you have sufficient USDC balance and market is active.")
        print("=" * 60)

if __name__ == "__main__":
    main() 