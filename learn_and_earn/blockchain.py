import os
import asyncio
import logging
from datetime import datetime
from web3 import Web3
from eth_account import Account

logger = logging.getLogger(__name__)

class LearnBlockchainService:
    """Learn & Earn Direct Private Key Disbursement"""

    def __init__(self):
        # Network configuration
        self.celo_rpc_url = os.getenv('CELO_RPC_URL', 'https://forno.celo.org')
        self.chain_id = int(os.getenv('CHAIN_ID', 42220))
        self.gooddollar_contract = os.getenv('GOODDOLLAR_CONTRACT', '0x62B8B11039FcfE5aB0C56E502b1C372A3d2a9c7A')

        # Private key for Learn & Earn disbursements
        self.learn_wallet_key = os.getenv('LEARN_WALLET_PRIVATE_KEY')

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.celo_rpc_url))

        if self.w3.is_connected():
            logger.info("✅ Connected to Celo network for Learn & Earn")
        else:
            logger.error("❌ Failed to connect to Celo network")

        logger.info("📚 Learn & Earn Private Key Service initialized")
        if self.learn_wallet_key:
            logger.info("✅ LEARN_WALLET_PRIVATE_KEY is configured")
        else:
            logger.warning("⚠️ LEARN_WALLET_PRIVATE_KEY is NOT configured - quiz rewards will fail")

    async def get_learn_wallet_balance(self) -> float:
        """Get the balance of the Learn wallet configured via LEARN_WALLET_PRIVATE_KEY"""
        try:
            if not self.learn_wallet_key:
                logger.error("❌ LEARN_WALLET_PRIVATE_KEY not configured")
                return 0.0

            # Load learn account
            if self.learn_wallet_key.startswith('0x'):
                learn_account = Account.from_key(self.learn_wallet_key)
            else:
                learn_account = Account.from_key('0x' + self.learn_wallet_key)

            # ERC20 balanceOf ABI
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }
            ]

            # Create contract instance
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.gooddollar_contract),
                abi=erc20_abi
            )

            # Get balance
            balance_wei = contract.functions.balanceOf(learn_account.address).call()
            balance_g = balance_wei / (10 ** 18)

            logger.info(f"💰 Learn wallet (LEARN_WALLET_PRIVATE_KEY) balance: {balance_g} G$")
            return balance_g

        except Exception as e:
            logger.error(f"❌ Error getting Learn wallet balance: {e}")
            return 0.0

    async def send_g_reward(self, wallet_address: str, amount: float, quiz_result_summary: dict = None) -> dict:
        """
        Send G$ rewards using LEARN_WALLET_PRIVATE_KEY

        Args:
            wallet_address: Recipient wallet address
            amount: Amount in G$ to send
            quiz_result_summary: Optional quiz result summary for logging

        Returns:
            Dict with success status, transaction hash, and details
        """
        try:
            logger.info(f"💰 Sending {amount} G$ reward using LEARN_WALLET_PRIVATE_KEY")

            if not self.learn_wallet_key:
                logger.error("❌ LEARN_WALLET_PRIVATE_KEY not configured")
                return {
                    "success": False,
                    "error": "LEARN_WALLET_PRIVATE_KEY not configured"
                }

            # Check balance first
            balance = await self.get_learn_wallet_balance()
            if balance < amount:
                logger.error(f"❌ Insufficient balance in Learn wallet: {balance} G$ < {amount} G$")
                return {
                    "success": False,
                    "error": "insufficient_balance",
                    "insufficient_balance": True
                }

            # Call the disbursement method
            return await self.disburse_quiz_reward(wallet_address, amount, f"quiz_{quiz_result_summary}")

        except Exception as e:
            logger.error(f"❌ Error sending G$ reward: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def disburse_quiz_reward(self, wallet_address: str, amount: float, quiz_id: str) -> dict:
        """Send G$ rewards via direct private key disbursement"""
        try:
            logger.info(f"💰 Quiz reward disbursement: {amount} G$ to {wallet_address[:8]}...")

            if not self.learn_wallet_key:
                logger.error("❌ LEARN_WALLET_PRIVATE_KEY not configured")
                return {"success": False, "error": "LEARN_WALLET_PRIVATE_KEY not configured"}

            # Load learn account
            if self.learn_wallet_key.startswith('0x'):
                learn_account = Account.from_key(self.learn_wallet_key)
            else:
                learn_account = Account.from_key('0x' + self.learn_wallet_key)

            # ERC20 token transfer ABI
            erc20_abi = [
                {
                    "constant": False,
                    "inputs": [
                        {"name": "_to", "type": "address"},
                        {"name": "_value", "type": "uint256"}
                    ],
                    "name": "transfer",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                }
            ]

            # Create contract instance for GoodDollar token
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.gooddollar_contract),
                abi=erc20_abi
            )

            # Convert amount to wei
            amount_wei = int(amount * (10 ** 18))

            # Get nonce and gas price
            nonce = self.w3.eth.get_transaction_count(learn_account.address)
            gas_price = int(self.w3.eth.gas_price * 1.2) # Add 20% buffer

            # Build transaction with 250,000 gas limit
            txn = contract.functions.transfer(
                Web3.to_checksum_address(wallet_address),
                amount_wei
            ).build_transaction({
                'chainId': self.chain_id,
                'gas': 250000,  # 250k gas limit for quiz rewards
                'gasPrice': gas_price,
                'nonce': nonce,
            })

            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(txn, self.learn_wallet_key)

            # Send transaction
            logger.info("📡 Sending quiz reward transaction...")
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()

            if not tx_hash_hex.startswith('0x'):
                tx_hash_hex = '0x' + tx_hash_hex

            logger.info(f"🔗 Transaction sent: {tx_hash_hex}")

            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt.status == 1:
                logger.info(f"✅ SMART CONTRACT SUCCESS: {amount} G$ quiz reward - TX: {tx_hash_hex}")
                logger.info(f"🔗 Explorer: https://explorer.celo.org/mainnet/tx/{tx_hash_hex}")
                logger.info(f"⛽ Gas used: {receipt.gasUsed}")
                logger.info(f"🔗 Block: {receipt.blockNumber}")
                return {
                    "success": True,
                    "tx_hash": tx_hash_hex,
                    "amount": amount,
                    "explorer_url": f"https://explorer.celo.org/mainnet/tx/{tx_hash_hex}",
                    "gas_used": receipt.gasUsed,
                    "block_number": receipt.blockNumber
                }
            else:
                logger.error(f"❌ Quiz reward transaction REVERTED: {tx_hash_hex}")
                logger.error(f"⛽ Gas used: {receipt.gasUsed}")
                logger.error(f"🔗 Block: {receipt.blockNumber}")
                logger.error(f"🔗 Explorer: https://explorer.celo.org/mainnet/tx/{tx_hash_hex}")
                logger.error(f"💰 Amount attempted: {amount} G$")
                logger.error(f"📍 Recipient: {wallet_address}")

                # Try to get revert reason
                try:
                    self.w3.eth.call(txn, receipt.blockNumber)
                except Exception as revert_error:
                    logger.error(f"❌ Revert reason: {revert_error}")

                return {
                    "success": False, 
                    "error": f"Transaction reverted on blockchain. Hash: {tx_hash_hex}",
                    "tx_hash": tx_hash_hex,
                    "explorer_url": f"https://explorer.celo.org/mainnet/tx/{tx_hash_hex}"
                }

        except Exception as e:
            logger.error(f"❌ Quiz reward error: {e}")
            return {"success": False, "error": str(e)}

# Create global instance
learn_blockchain_service = LearnBlockchainService()

# Legacy function for backward compatibility
def disburse_rewards(wallet_address, amount, score):
    """Legacy function - now requires direct private key disbursement"""
    return learn_blockchain_service.disburse_quiz_reward(wallet_address, amount, f"legacy_quiz_{score}")
