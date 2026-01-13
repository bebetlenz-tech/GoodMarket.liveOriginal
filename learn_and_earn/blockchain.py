import os
import asyncio
import logging
from datetime import datetime
from web3 import Web3
from eth_account import Account

logger = logging.getLogger(__name__)

class LearnBlockchainService:
    """Learn & Earn Smart Contract Disbursement Service
    
    Uses the deployed LearnAndEarnRewards smart contract for secure G$ disbursements.
    Falls back to direct transfer only if contract is not configured.
    """

    def __init__(self):
        self.celo_rpc_url = os.getenv('CELO_RPC_URL', 'https://forno.celo.org')
        self.chain_id = int(os.getenv('CHAIN_ID', 42220))
        self.gooddollar_address = os.getenv('GOODDOLLAR_CONTRACT', '0x62B8B11039FcfE5aB0C56E502b1C372A3d2a9c7A')
        self.contract_address = os.getenv('LEARN_EARN_CONTRACT_ADDRESS')
        self._wallet_key = os.getenv('LEARN_WALLET_PRIVATE_KEY')

        self.w3 = Web3(Web3.HTTPProvider(self.celo_rpc_url))
        self.contract = None
        self.owner_account = None

        if self.w3.is_connected():
            logger.info("Connected to Celo network for Learn & Earn")
        else:
            logger.error("Failed to connect to Celo network")

        self._initialize()

    def _initialize(self):
        """Initialize contract and wallet"""
        try:
            if self.contract_address:
                self.contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(self.contract_address),
                    abi=self._get_contract_abi()
                )
                logger.info(f"Learn & Earn Contract loaded: {self.contract_address[:10]}...")
            else:
                logger.warning("Learn & Earn contract not configured")

            if self._wallet_key:
                key = self._wallet_key if self._wallet_key.startswith('0x') else '0x' + self._wallet_key
                self.owner_account = Account.from_key(key)
                logger.info("Learn & Earn wallet configured")
            else:
                logger.warning("Learn & Earn wallet not configured")

        except Exception as e:
            logger.error(f"Initialization error: {type(e).__name__}")

    @property
    def is_configured(self) -> bool:
        """Check if the service is properly configured (without exposing private key)"""
        return self.owner_account is not None

    def _get_contract_abi(self):
        """Get minimal ABI for contract interactions"""
        return [
            {"inputs": [], "name": "getContractBalance", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "recipient", "type": "address"}, {"name": "amount", "type": "uint256"}, {"name": "quizId", "type": "string"}], "name": "disburseReward", "outputs": [{"type": "bytes32"}], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "recipient", "type": "address"}, {"name": "quizId", "type": "string"}], "name": "isQuizRewardClaimed", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "paused", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
        ]

    def _get_erc20_abi(self):
        """Get ERC20 ABI for balance checks"""
        return [
            {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
        ]

    async def get_contract_balance(self) -> float:
        """Get the G$ balance of the Learn & Earn contract"""
        try:
            if not self.contract:
                logger.error("Contract not configured")
                return 0.0

            balance_wei = self.contract.functions.getContractBalance().call()
            balance_g = balance_wei / (10 ** 18)
            logger.info(f"Contract balance: {balance_g:.2f} G$")
            return balance_g

        except Exception as e:
            logger.error(f"Error getting contract balance: {type(e).__name__}")
            return 0.0

    async def get_learn_wallet_balance(self) -> float:
        """Get the G$ balance of the Learn wallet (for legacy compatibility)"""
        try:
            if self.contract:
                return await self.get_contract_balance()

            if not self.owner_account:
                return 0.0

            erc20 = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.gooddollar_address),
                abi=self._get_erc20_abi()
            )
            balance_wei = erc20.functions.balanceOf(self.owner_account.address).call()
            return balance_wei / (10 ** 18)

        except Exception as e:
            logger.error(f"Error getting balance: {type(e).__name__}")
            return 0.0

    async def send_g_reward(self, wallet_address: str, amount: float, quiz_result_summary: dict = None) -> dict:
        """Send G$ rewards - uses smart contract"""
        try:
            quiz_id = f"quiz_{hash(str(quiz_result_summary)) % 1000000}" if quiz_result_summary else f"quiz_{int(datetime.now().timestamp())}"
            return await self.disburse_quiz_reward(wallet_address, amount, quiz_id)

        except Exception as e:
            logger.error(f"Error sending reward: {type(e).__name__}")
            return {"success": False, "error": "Failed to send reward"}

    async def disburse_quiz_reward(self, wallet_address: str, amount: float, quiz_id: str) -> dict:
        """Send G$ rewards via smart contract"""
        try:
            logger.info(f"Quiz reward: {amount} G$ to {wallet_address[:10]}...")

            if not self.contract:
                return {"success": False, "error": "Reward contract not configured. Please contact support."}

            if not self.owner_account:
                return {"success": False, "error": "Reward system not configured. Please contact support."}

            if not self._wallet_key:
                return {"success": False, "error": "Reward system not configured. Please contact support."}

            # Check if contract is paused
            try:
                is_paused = self.contract.functions.paused().call()
                if is_paused:
                    return {"success": False, "error": "Reward system is temporarily paused. Please try again later."}
            except:
                pass

            # Check contract balance
            balance = await self.get_contract_balance()
            if balance < amount:
                logger.error(f"Insufficient contract balance: {balance:.2f} G$ < {amount} G$")
                return {
                    "success": False,
                    "error": "Rewards pool is currently depleted. Please try again later.",
                    "insufficient_balance": True
                }

            # Check if reward already claimed
            try:
                already_claimed = self.contract.functions.isQuizRewardClaimed(
                    Web3.to_checksum_address(wallet_address),
                    quiz_id
                ).call()
                if already_claimed:
                    return {"success": False, "error": "Reward already claimed for this quiz."}
            except:
                pass

            # Build and send transaction
            amount_wei = int(amount * (10 ** 18))
            nonce = self.w3.eth.get_transaction_count(self.owner_account.address)
            gas_price = int(self.w3.eth.gas_price * 1.2)

            txn = self.contract.functions.disburseReward(
                Web3.to_checksum_address(wallet_address),
                amount_wei,
                quiz_id
            ).build_transaction({
                'chainId': self.chain_id,
                'gas': 500000,
                'gasPrice': gas_price,
                'nonce': nonce,
            })

            signed_txn = self.w3.eth.account.sign_transaction(txn, self._wallet_key)
            
            logger.info("Sending reward transaction...")
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            if not tx_hash_hex.startswith('0x'):
                tx_hash_hex = '0x' + tx_hash_hex

            logger.info(f"Transaction sent: {tx_hash_hex}")

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt.status == 1:
                logger.info(f"Reward sent: {amount} G$ - TX: {tx_hash_hex}")
                return {
                    "success": True,
                    "tx_hash": tx_hash_hex,
                    "amount": amount,
                    "explorer_url": f"https://celoscan.io/tx/{tx_hash_hex}",
                    "gas_used": receipt.gasUsed,
                    "block_number": receipt.blockNumber
                }
            else:
                logger.error(f"Transaction reverted: {tx_hash_hex}")
                return {
                    "success": False,
                    "error": "Transaction failed. Please try again.",
                    "tx_hash": tx_hash_hex,
                    "explorer_url": f"https://celoscan.io/tx/{tx_hash_hex}"
                }

        except Exception as e:
            error_msg = str(e)
            # Hide sensitive info from error messages
            if 'private' in error_msg.lower() or 'key' in error_msg.lower():
                error_msg = "Configuration error"
            elif 'insufficient' in error_msg.lower():
                error_msg = "Rewards pool is currently depleted"
            elif 'nonce' in error_msg.lower():
                error_msg = "Transaction conflict. Please try again."
            else:
                error_msg = "Failed to process reward. Please try again."
            
            logger.error(f"Quiz reward error: {type(e).__name__}")
            return {"success": False, "error": error_msg}


learn_blockchain_service = LearnBlockchainService()


def disburse_rewards(wallet_address, amount, score):
    """Legacy function for backward compatibility"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        learn_blockchain_service.disburse_quiz_reward(wallet_address, amount, f"legacy_quiz_{score}")
    )
