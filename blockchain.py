
import requests
from datetime import datetime, timedelta, timezone
import logging
import os
import time

# UBI verification cache - stores results per wallet to avoid slow blockchain queries
_ubi_cache = {}
_UBI_CACHE_TTL = 300  # 5 minutes cache for UBI verification results
_UBI_CACHE_MAX_SIZE = 1000  # Maximum cache entries to prevent memory bloat


def _cleanup_expired_cache():
    """Remove expired entries from cache to prevent memory leaks"""
    global _ubi_cache
    current_time = time.time()
    expired_keys = [
        key for key, (_, timestamp) in _ubi_cache.items()
        if current_time - timestamp >= _UBI_CACHE_TTL
    ]
    for key in expired_keys:
        del _ubi_cache[key]
    
    # If still too large, remove oldest entries
    if len(_ubi_cache) > _UBI_CACHE_MAX_SIZE:
        sorted_keys = sorted(_ubi_cache.keys(), key=lambda k: _ubi_cache[k][1])
        for key in sorted_keys[:len(_ubi_cache) - _UBI_CACHE_MAX_SIZE]:
            del _ubi_cache[key]

# Celo Network Configuration - Using environment variables from secrets
CELO_CHAIN_ID = int(os.getenv("CHAIN_ID", "42220"))  # Celo Mainnet Chain ID
CELO_RPC = os.getenv("CELO_RPC_URL", "https://forno.celo.org")  # Celo RPC endpoint from secrets

# GoodDollar Contracts - Using environment variables from secrets
GOODDOLLAR_CONTRACTS = {
    # Main UBI Contract - ERC1967 Proxy
    "UBI_PROXY": os.getenv("UBI_PROXY_CONTRACT", "0x43d72Ff17701B2DA814620735C39C620Ce0ea4A1"),

    # Implementation contract (will be auto-discovered)
    "UBI_IMPLEMENTATION": "",  # Will be filled by _validate_ubi_contract()

    # Supporting contracts
    "GOODDOLLAR_TOKEN": os.getenv("GOODDOLLAR_TOKEN_CONTRACT", "0x62B8B11039FcfE5aB0C56E502b1C372A3d2a9c7A"),
}

# Event signatures derived from implementation contract ABI
UBI_EVENT_SIGNATURES = {
    # Transfer Events (ERC20)
    "TRANSFER": "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",

    # UBI Events (from implementation contract ABI)
    "UBI_CLAIMED": "0x89ed24731df6b066e4c5186901fffdba18cd9a10f07494aff900bdee260d1304",  # UBIClaimed(address,uint256)
    "UBI_CALCULATED": "0x836fa39995340265746dfe9587d9fe5c5de35b7bce778afd9b124ce1cfeafdc4",  # UBICalculated(uint256,uint256,uint256)
    "UBI_CYCLE_CALCULATED": "0x83e0d535b9e84324e0a25922406398d6ff5f96d0c686204ee490e16d7670566f",  # UBICycleCalculated(uint256,uint256,uint256,uint256)
}


def _get_implementation_address(proxy_address: str) -> str:
    """Get the implementation contract address from an ERC1967 proxy"""
    try:
        # ERC1967 implementation slot: keccak256("eip1967.proxy.implementation") - 1
        implementation_slot = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"

        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getStorageAt",
            "params": [proxy_address, implementation_slot, "latest"],
            "id": 1
        }

        response = requests.post(CELO_RPC, json=payload, timeout=10)
        result = response.json()

        if "result" in result and result["result"]:
            # Extract address from storage slot (last 20 bytes)
            storage_value = result["result"]
            if storage_value and storage_value != "0x0000000000000000000000000000000000000000000000000000000000000000":
                implementation_address = "0x" + storage_value[-40:]  # Last 20 bytes = 40 hex chars
                print(f"🔍 DEBUG: Found implementation contract: {implementation_address}")
                return implementation_address

        print(f"🔍 DEBUG: Could not find implementation address for proxy {proxy_address}")
        return ""
    except Exception as e:
        print(f"🔍 DEBUG: Exception getting implementation address: {e}")
        return ""


def _get_contract_abi(contract_address: str) -> dict:
    """Fetch contract ABI from Celo Explorer API"""
    try:
        # Celo Explorer API endpoint for contract ABI
        api_url = f"https://explorer.celo.org/api?module=contract&action=getabi&address={contract_address}"

        response = requests.get(api_url, timeout=10)
        result = response.json()

        if result.get("status") == "1" and result.get("result"):
            import json
            abi = json.loads(result["result"])
            print(f"🔍 DEBUG: Successfully fetched ABI for {contract_address}")
            return abi
        else:
            print(f"🔍 DEBUG: Could not fetch ABI for {contract_address}: {result.get('message', 'Unknown error')}")
            return {}
    except Exception as e:
        print(f"🔍 DEBUG: Exception fetching ABI: {e}")
        return {}


def _extract_event_signatures_from_abi(abi: list) -> dict:
    """Extract event signatures from contract ABI"""
    try:
        from Crypto.Hash import keccak
    except ImportError:
        # Fallback to hashlib if pycryptodome not available
        import hashlib
        def keccak256(data):
            return hashlib.sha3_256(data).hexdigest()
    else:
        def keccak256(data):
            k = keccak.new(digest_bits=256)
            k.update(data)
            return k.hexdigest()

    events = {}
    for item in abi:
        if item.get("type") == "event":
            event_name = item["name"]
            inputs = item.get("inputs", [])

            # Build event signature string
            param_types = []
            for input_param in inputs:
                param_types.append(input_param["type"])

            signature_string = f"{event_name}({','.join(param_types)})"

            # Calculate keccak256 hash (first 32 bytes = 64 hex chars)
            signature_hash = "0x" + keccak256(signature_string.encode())[:64]

            events[event_name.upper()] = signature_hash
            print(f"🔍 DEBUG: Event {event_name}: {signature_string} -> {signature_hash}")

    return events


def _validate_ubi_contract() -> bool:
    """Validate UBI Proxy contract and get implementation ABI for event signatures"""
    try:
        ubi_proxy_address = GOODDOLLAR_CONTRACTS["UBI_PROXY"]
        print(f"🔍 DEBUG: Validating UBI Proxy contract: {ubi_proxy_address}")

        # First get the implementation contract address
        implementation_address = _get_implementation_address(ubi_proxy_address)
        if not implementation_address:
            print(f"🔍 DEBUG: Could not find implementation contract address")
            return False

        print(f"🔍 DEBUG: Implementation contract: {implementation_address}")

        # Get the implementation contract ABI (which contains the actual events)
        implementation_abi = _get_contract_abi(implementation_address)
        if implementation_abi:
            extracted_events = _extract_event_signatures_from_abi(implementation_abi)

            # Check if our current signatures match
            print(f"🔍 DEBUG: Found {len(extracted_events)} events in implementation ABI")
            print(f"🔍 DEBUG: Currently tracking {len(UBI_EVENT_SIGNATURES)} event signatures")

            # Look for UBI-related events
            ubi_events = {}
            for event_name, signature in extracted_events.items():
                if any(keyword in event_name.lower() for keyword in ['ubi', 'claim', 'reward', 'distribute']):
                    ubi_events[event_name] = signature
                    print(f"🔍 DEBUG: Found UBI event: {event_name} -> {signature}")

            # Update our signatures with any new ones found
            if ubi_events:
                print(f"🔍 DEBUG: Found {len(ubi_events)} UBI-related events in implementation contract")
                # Store the implementation address for future reference
                GOODDOLLAR_CONTRACTS["UBI_IMPLEMENTATION"] = implementation_address

                # Log any mismatches with current signatures
                for event_name, our_sig in UBI_EVENT_SIGNATURES.items():
                    if event_name in extracted_events:
                        abi_sig = extracted_events[event_name]
                        if our_sig != abi_sig:
                            print(f"🔍 DEBUG: ⚠️  Signature mismatch for {event_name}")
                            print(f"🔍 DEBUG:    Ours: {our_sig}")
                            print(f"🔍 DEBUG:    ABI:  {abi_sig}")

            return True
        else:
            print(f"🔍 DEBUG: Could not get implementation contract ABI")
            return False

    except Exception as e:
        print(f"🔍 DEBUG: Exception during contract validation: {e}")
        return False


# UBI valid for 24 hours
CUTOFF_HOURS = 24  # 24 hours

log = logging.getLogger("blockchain")


def _format_timestamp(block_number: int) -> str:
    """Format timestamp to show relative time and exact datetime"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBlockByNumber",
            "params": [hex(block_number), False],
            "id": 1
        }
        response = requests.post(CELO_RPC, json=payload, timeout=10)
        result = response.json()

        if "result" in result and result["result"]:
            timestamp = int(result["result"]["timestamp"], 16)
            block_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            diff = now - block_time

            if diff.days > 0:
                relative = f"{diff.days}d ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                relative = f"{hours}h ago"
            else:
                minutes = diff.seconds // 60
                relative = f"{minutes}m ago"

            exact_time = block_time.strftime("%b %d %Y %H:%M:%S %p (+00:00 UTC)")
            return f"{relative} | {exact_time}"
    except Exception as e:
        print(f"🔍 DEBUG: Error formatting timestamp for block {block_number}: {e}")

    return f"Block #{block_number}"


def _topic_for_address(wallet: str) -> str:
    """Convert wallet to padded topic format."""
    return "0x" + ("0" * 24) + wallet.lower().replace("0x", "")


def _get_latest_block_number() -> int:
    """Get the latest block number from Celo blockchain"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "params": [],
            "id": 1
        }
        response = requests.post(CELO_RPC, json=payload, timeout=10)
        result = response.json()
        return int(result["result"], 16)
    except Exception as e:
        print(f"🔍 DEBUG: Error getting latest block: {e}")
        return 0


def _calculate_block_range(hours_back: int) -> tuple:
    """Calculate approximate block range for the given hours back"""
    blocks_per_hour = 720  # Celo ~5 second block time
    latest_block = _get_latest_block_number()
    from_block = latest_block - (hours_back * blocks_per_hour)

    print(f"🔍 DEBUG: Block range: {from_block} to {latest_block} (last {hours_back} hours)")
    return hex(from_block), hex(latest_block)


def _check_contract_for_ubi_activity(contract_name: str, contract_address: str, wallet_address: str, from_block: str, to_block: str) -> list:
    """Check a specific contract for UBI-related activity"""
    activities = []

    print(f"🔍 DEBUG: Checking {contract_name} ({contract_address[:10]}...)")

    # Check for G$ transfers FROM this contract TO user
    if contract_address != GOODDOLLAR_CONTRACTS["GOODDOLLAR_TOKEN"]:  # Don't check token contract as sender
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": from_block,
                "toBlock": to_block,
                "address": GOODDOLLAR_CONTRACTS["GOODDOLLAR_TOKEN"],
                "topics": [
                    UBI_EVENT_SIGNATURES["TRANSFER"],
                    _topic_for_address(contract_address),  # FROM: this contract
                    _topic_for_address(wallet_address)     # TO: user wallet
                ]
            }],
            "id": 1
        }

        try:
            response = requests.post(CELO_RPC, json=payload, timeout=15)
            result = response.json()

            if "error" not in result:
                logs = result.get("result", [])
                print(f"🔍 DEBUG:   Found {len(logs)} G$ transfers from {contract_name}")

                for log_entry in logs:
                    block_num = int(log_entry.get("blockNumber", "0x0"), 16)
                    tx_hash = log_entry.get("transactionHash", "Unknown")
                    timestamp_info = _format_timestamp(block_num)

                    # Extract amount
                    amount_hex = log_entry.get("data", "0x0")
                    try:
                        amount_wei = int(amount_hex, 16)
                        amount_g = amount_wei / (10 ** 18)
                    except:
                        amount_g = 0

                    activities.append({
                        "contract": contract_name,
                        "contract_address": contract_address,
                        "block": block_num,
                        "tx_hash": tx_hash,
                        "timestamp": timestamp_info,
                        "method": "G$ transfer",
                        "status": "success",
                        "amount": f"{amount_g:.6f} G$",
                        "activity_type": "transfer"
                    })

                    print(f"🔍 DEBUG:     ✅ Transfer: {amount_g:.6f} G$ at block #{block_num}")
            else:
                print(f"🔍 DEBUG:   RPC error for {contract_name}: {result.get('error', {}).get('message', 'Unknown')}")
        except Exception as e:
            print(f"🔍 DEBUG:   Exception checking {contract_name}: {e}")

    # Check for UBI-specific events on this contract
    for event_name, event_signature in UBI_EVENT_SIGNATURES.items():
        if event_name == "TRANSFER":  # Already checked above
            continue

        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": from_block,
                "toBlock": to_block,
                "address": contract_address,
                "topics": [
                    event_signature,
                    _topic_for_address(wallet_address)  # User as first indexed parameter
                ]
            }],
            "id": 1
        }

        try:
            response = requests.post(CELO_RPC, json=payload, timeout=15)
            result = response.json()

            if "error" not in result:
                logs = result.get("result", [])
                if len(logs) > 0:
                    print(f"🔍 DEBUG:   Found {len(logs)} {event_name} events")

                    for log_entry in logs:
                        block_num = int(log_entry.get("blockNumber", "0x0"), 16)
                        tx_hash = log_entry.get("transactionHash", "Unknown")
                        timestamp_info = _format_timestamp(block_num)

                        # Extract amount if available
                        amount_hex = log_entry.get("data", "0x0")
                        try:
                            amount_wei = int(amount_hex, 16)
                            amount_g = amount_wei / (10 ** 18)
                        except:
                            amount_g = 0

                        activities.append({
                            "contract": contract_name,
                            "contract_address": contract_address,
                            "block": block_num,
                            "tx_hash": tx_hash,
                            "timestamp": timestamp_info,
                            "method": event_name.lower(),
                            "status": "success",
                            "amount": f"{amount_g:.6f} G$" if amount_g > 0 else "Event logged",
                            "activity_type": "event"
                        })

                        print(f"🔍 DEBUG:     ✅ {event_name}: {amount_g:.6f} G$ at block #{block_num}")
        except Exception as e:
            print(f"🔍 DEBUG:   Exception checking {event_name} on {contract_name}: {e}")

    return activities


def has_recent_ubi_claim(wallet_address: str) -> dict:
    """
    Check for UBI claims specifically from the UBI Proxy contract:
    0x43d72Ff17701B2DA814620735C39C620Ce0ea4A1
    
    PERFORMANCE: Results are cached for 5 minutes per wallet to avoid slow blockchain queries.
    """
    global _ubi_cache
    
    # Cleanup expired cache entries to prevent memory leaks
    _cleanup_expired_cache()
    
    # Check cache first to avoid slow blockchain queries
    cache_key = wallet_address.lower()
    current_time = time.time()
    
    if cache_key in _ubi_cache:
        cached_result, cache_timestamp = _ubi_cache[cache_key]
        if current_time - cache_timestamp < _UBI_CACHE_TTL:
            print(f"🔍 DEBUG: ⚡ Using cached UBI result for {wallet_address[:10]}... (age: {int(current_time - cache_timestamp)}s)")
            return cached_result
    
    try:
        print(f"🔍 DEBUG: 🎯 UBI PROXY CONTRACT CHECK for wallet: {wallet_address}")
        print(f"🔍 DEBUG: Focusing on UBI Proxy: 0x43d72Ff17701B2DA814620735C39C620Ce0ea4A1")
        print(f"🔍 DEBUG: Looking for UBI claim events in the last 48 hours")

        # Validate contract ABI and event signatures
        print(f"🔍 DEBUG: Validating contract ABI...")
        _validate_ubi_contract()

        # Extended to 48 hours to catch recent claims (Celo blockchain delays)
        search_hours = 48  # Check last 48 hours to account for blockchain indexing delays
        from_block, to_block = _calculate_block_range(search_hours)

        ubi_proxy_address = GOODDOLLAR_CONTRACTS["UBI_PROXY"]
        gooddollar_token = GOODDOLLAR_CONTRACTS["GOODDOLLAR_TOKEN"]

        all_activities = []

        print(f"\n🔍 DEBUG: === CHECKING UBI PROXY CONTRACT ===")

        # First, check if there are ANY UBI events from this contract (without wallet filter)
        test_payload = {
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": from_block,
                "toBlock": to_block,
                "address": ubi_proxy_address,
                "topics": [UBI_EVENT_SIGNATURES["UBI_CLAIMED"]]
            }],
            "id": 1
        }

        try:
            test_response = requests.post(CELO_RPC, json=test_payload, timeout=15)
            test_result = test_response.json()
            if "error" not in test_result:
                all_ubi_events = test_result.get("result", [])
                print(f"🔍 DEBUG: Total UBI_CLAIMED events in timeframe: {len(all_ubi_events)}")
                if len(all_ubi_events) > 0:
                    print(f"🔍 DEBUG: Sample event topics: {all_ubi_events[0].get('topics', [])}")
            else:
                print(f"🔍 DEBUG: Error checking general UBI events: {test_result.get('error')}")
        except Exception as e:
            print(f"🔍 DEBUG: Exception checking general events: {e}")

        # Check for G$ transfers FROM UBI Proxy TO user
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": from_block,
                "toBlock": to_block,
                "address": gooddollar_token,
                "topics": [
                    UBI_EVENT_SIGNATURES["TRANSFER"],
                    _topic_for_address(ubi_proxy_address),  # FROM: UBI Proxy
                    _topic_for_address(wallet_address)      # TO: user wallet
                ]
            }],
            "id": 1
        }

        try:
            response = requests.post(CELO_RPC, json=payload, timeout=15)
            result = response.json()

            if "error" not in result:
                logs = result.get("result", [])
                print(f"🔍 DEBUG: Found {len(logs)} G$ transfers from UBI Proxy to user")

                for log_entry in logs:
                    block_num = int(log_entry.get("blockNumber", "0x0"), 16)
                    tx_hash = log_entry.get("transactionHash", "Unknown")
                    timestamp_info = _format_timestamp(block_num)

                    # Extract amount
                    amount_hex = log_entry.get("data", "0x0")
                    try:
                        amount_wei = int(amount_hex, 16)
                        amount_g = amount_wei / (10 ** 18)
                    except:
                        amount_g = 0

                    all_activities.append({
                        "contract": "UBI Proxy",
                        "contract_address": ubi_proxy_address,
                        "block": block_num,
                        "tx_hash": tx_hash,
                        "timestamp": timestamp_info,
                        "method": "UBI claim",
                        "status": "success",
                        "amount": f"{amount_g:.6f} G$",
                        "activity_type": "ubi_claim"
                    })

                    print(f"🔍 DEBUG:     ✅ UBI Claim: {amount_g:.6f} G$ at block #{block_num}")
            else:
                print(f"🔍 DEBUG:   RPC error: {result.get('error', {}).get('message', 'Unknown')}")
        except Exception as e:
            print(f"🔍 DEBUG:   Exception checking UBI Proxy: {e}")

        # Check for UBI-specific events on UBI Proxy contract
        for event_name, event_signature in UBI_EVENT_SIGNATURES.items():
            if event_name == "TRANSFER":  # Already checked above
                continue

            print(f"🔍 DEBUG:   Checking {event_name} events...")

            # Different topic configurations for different events
            topics = [event_signature]

            # UBI claim events typically have the claimer as first indexed parameter
            if event_name in ["UBI_CLAIMED", "CLAIM", "REWARD_CLAIMED", "UBI_DISTRIBUTED", "DAILY_UBI"]:
                topics.append(_topic_for_address(wallet_address))  # claimer as indexed parameter
            else:
                # For other events, try both with and without wallet filter
                topics.append(None)  # Will check without specific wallet filter first

            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getLogs",
                "params": [{
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "address": ubi_proxy_address,
                    "topics": topics
                }],
                "id": 1
            }

            print(f"🔍 DEBUG:   Query: address={ubi_proxy_address[:10]}..., topics={[t[:10]+'...' if t else None for t in topics]}")

            try:
                response = requests.post(CELO_RPC, json=payload, timeout=15)
                result = response.json()

                if "error" not in result:
                    logs = result.get("result", [])

                    # Filter logs manually if we didn't filter by wallet in topics
                    if event_name not in ["UBI_CLAIMED", "CLAIM", "REWARD_CLAIMED", "UBI_DISTRIBUTED", "DAILY_UBI"]:
                        # Check if any topic contains our wallet address
                        filtered_logs = []
                        wallet_topic = _topic_for_address(wallet_address)
                        for log in logs:
                            log_topics = log.get("topics", [])
                            if wallet_topic in log_topics:
                                filtered_logs.append(log)
                        logs = filtered_logs

                    if len(logs) > 0:
                        print(f"🔍 DEBUG:   Found {len(logs)} {event_name} events")

                        for log_entry in logs:
                            block_num = int(log_entry.get("blockNumber", "0x0"), 16)
                            tx_hash = log_entry.get("transactionHash", "Unknown")
                            timestamp_info = _format_timestamp(block_num)

                            # Try to extract amount from data field
                            amount_str = "Event logged"
                            try:
                                data = log_entry.get("data", "0x")
                                if data and data != "0x":
                                    # For UBI events, amount is typically in the data field
                                    amount_wei = int(data, 16)
                                    amount_g = amount_wei / (10 ** 18)
                                    amount_str = f"{amount_g:.6f} G$"
                            except:
                                # If data parsing fails, check topics for amount
                                try:
                                    topics = log_entry.get("topics", [])
                                    if len(topics) > 2:  # Some events have amount as indexed parameter
                                        amount_wei = int(topics[2], 16)
                                        amount_g = amount_wei / (10 ** 18)
                                        amount_str = f"{amount_g:.6f} G$"
                                except:
                                    pass

                            all_activities.append({
                                "contract": "UBI Proxy",
                                "contract_address": ubi_proxy_address,
                                "block": block_num,
                                "tx_hash": tx_hash,
                                "timestamp": timestamp_info,
                                "method": event_name.lower().replace("_", " "),
                                "status": "success",
                                "amount": amount_str,
                                "activity_type": "ubi_event"
                            })

                            print(f"🔍 DEBUG:     ✅ {event_name}: {amount_str} at block #{block_num}")
                else:
                    error_msg = result.get("error", {}).get("message", "Unknown RPC error")
                    print(f"🔍 DEBUG:   RPC error for {event_name}: {error_msg}")
            except Exception as e:
                print(f"🔍 DEBUG:   Exception checking {event_name}: {e}")

        print(f"\n🔍 DEBUG: === FINAL RESULTS ===")
        print(f"🔍 DEBUG: Total UBI activities found: {len(all_activities)}")
        
        # If no activities found, try checking latest block directly
        if len(all_activities) == 0:
            print(f"🔍 DEBUG: No activities found in {search_hours}h window, checking latest claim status...")
            try:
                # Quick check: Get user's latest claim time from UBI contract
                latest_block = _get_latest_block_number()
                print(f"🔍 DEBUG: Current latest block: {latest_block}")
                print(f"🔍 DEBUG: Searched from block {from_block} to {to_block}")
            except Exception as e:
                print(f"🔍 DEBUG: Latest block check failed: {e}")

        if len(all_activities) > 0:
            # Sort by block number to get latest
            all_activities.sort(key=lambda x: x['block'], reverse=True)
            latest_activity = all_activities[0]

            # Categorize activities
            claims = [a for a in all_activities if a["activity_type"] == "ubi_claim"]
            events = [a for a in all_activities if a["activity_type"] == "ubi_event"]

            success_message = f"✅ UBI VERIFICATION SUCCESS!\n\n"
            success_message += f"🎯 Found {len(all_activities)} UBI activities from UBI Proxy contract\n"
            success_message += f"   💰 UBI Claims: {len(claims)}\n"
            success_message += f"   📋 Events: {len(events)}\n\n"

            success_message += f"🕐 Most Recent Activity:\n"
            success_message += f"   Contract: {latest_activity['contract']}\n"
            success_message += f"   Type: {latest_activity['method']}\n"
            success_message += f"   Amount: {latest_activity['amount']}\n"
            success_message += f"   Block: #{latest_activity['block']}\n"
            success_message += f"   Time: {latest_activity['timestamp']}\n"
            success_message += f"   Tx: {latest_activity['tx_hash'][:16]}...\n"

            if len(all_activities) > 1:
                success_message += f"\n📊 All UBI Activities (last 24 hours):\n"
                for i, activity in enumerate(all_activities[:5], 1):  # Show top 5
                    success_message += f"   {i}. {activity['amount']} ({activity['method']}) - {activity['timestamp']}\n"

                if len(all_activities) > 5:
                    success_message += f"   ... and {len(all_activities) - 5} more activities\n"

            print(f"🔍 DEBUG: ✅ SUCCESS! Found {len(all_activities)} UBI activities")

            result = {
                "status": "success",
                "message": success_message,
                "activities": all_activities,
                "summary": {
                    "total_activities": len(all_activities),
                    "claims": len(claims),
                    "events": len(events),
                    "contracts_involved": 1,  # Only UBI Proxy
                    "latest_activity": latest_activity
                }
            }
            # Cache the successful result
            _ubi_cache[cache_key] = (result, current_time)
            return result
        else:
            print(f"🔍 DEBUG: ❌ No UBI activities found from UBI Proxy contract in last {search_hours} hours")
            
            # Provide more specific error message
            error_msg = f"""⚠️ No recent UBI claim detected in the last {search_hours} hours.

Please:
1. Visit goodwallet.xyz or gooddapp.org
2. Claim your daily G$ (UBI)
3. Wait 2-3 minutes for blockchain confirmation
4. Try logging in again

Note: It may take a few minutes for your claim to be confirmed on the Celo blockchain."""
            
            result = {
                "status": "error",
                "message": error_msg
            }
            # Cache the error result too to avoid repeated slow queries
            _ubi_cache[cache_key] = (result, current_time)
            return result

    except Exception as e:
        print(f"🔍 DEBUG: Exception in UBI Proxy check: {e}")
        # Don't cache exceptions - let them retry
        return {"status": "error", "message": f"⚠️ UBI verification failed: {e}"}


def get_gooddollar_balance(wallet_address: str) -> dict:
    """Get GoodDollar token balance for a wallet address"""
    try:
        print(f"🔍 DEBUG: Checking GoodDollar balance for {wallet_address}")

        # Initialize Web3 connection
        import requests
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(CELO_RPC))

        if not w3.is_connected():
            print("🔍 DEBUG: Failed to connect to Celo network")
            return {
                "success": False,
                "error": "Failed to connect to Celo network",
                "balance": 0,
                "balance_formatted": "Connection Error"
            }

        # GoodDollar ERC20 ABI for balance checking
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            }
        ]

        # Use GoodDollar token contract address
        gooddollar_token = GOODDOLLAR_CONTRACTS["GOODDOLLAR_TOKEN"]
        print(f"🔍 DEBUG: Using GoodDollar token contract: {gooddollar_token}")

        # Create contract instance
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(gooddollar_token),
            abi=erc20_abi
        )

        # Get balance
        wallet_checksum = Web3.to_checksum_address(wallet_address)
        balance_wei = contract.functions.balanceOf(wallet_checksum).call()

        # Convert from wei to G$ (18 decimals)
        balance_g = balance_wei / (10 ** 18)

        print(f"🔍 DEBUG: Balance for {wallet_address}: {balance_g} G$")

        return {
            "success": True,
            "balance": float(balance_g),
            "balance_formatted": f"{balance_g:.6f} G$",
            "wallet": wallet_address,
            "contract": gooddollar_token
        }

    except Exception as e:
        print(f"🔍 DEBUG: Balance check error: {e}")
        return {
            "success": False,
            "error": str(e),
            "balance": 0,
            "balance_formatted": "Error loading balance"
        }


if __name__ == "__main__":
    test_wallet = "0xFf00A683f7bD77665754A65F2B82fdEFc4371a50"
    result = has_recent_ubi_claim(test_wallet)
    print(result["message"])
