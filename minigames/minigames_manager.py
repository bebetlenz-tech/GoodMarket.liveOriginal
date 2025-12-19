import os
import json
import logging
import random
import uuid
from datetime import datetime, date
from supabase_client import get_supabase_client
from .blockchain import minigames_blockchain

logger = logging.getLogger(__name__)

class MinigamesManager:
    """
    Manages all minigames and rewards
    
    DEPOSIT & WITHDRAWAL FLOW:
    1. Users deposit G$ to MERCHANT_ADDRESS (shown as "Deposit Address" to users)
    2. Deposits are tracked in minigame_balances table
    3. Users play games and accumulate winnings
    4. Withdrawals are sent from GAMES_KEY to user's wallet
    """

    def __init__(self):
        self.supabase = get_supabase_client()
        self.blockchain_service = minigames_blockchain

        # Deposit configurations
        self.MIN_DEPOSIT = 100.0  # Minimum deposit 100 G$
        self.MAX_DEPOSIT = 500.0  # Maximum deposit per day 500 G$
        
        # Withdrawal configurations
        self.MIN_WITHDRAWAL = 100.0  # Minimum withdrawal 100 G$
        self.MAX_WITHDRAWAL = 10000.0  # Maximum withdrawal 10,000 G$

        # Game configurations
        self.game_configs = {
            'crash_game': {
                'max_plays_per_day': 20,  # Maximum 20 plays per day
                'min_bet': 10.0,  # Minimum bet 10 G$
                'max_bet': 250.0,  # Maximum bet 250 G$
                'base_reward': 10,
                'min_multiplier': 1.20,
                'max_multiplier': 5.00  # Maximum 5x crash multiplier
            },
            'coin_flip': {
                'max_plays_per_day': 20,  # Maximum 20 plays per day
                'min_bet': 50.0,  # Minimum bet 50 G$
                'max_bet': 250.0,  # Maximum bet 250 G$
                'win_multiplier': 2.0  # 2x payout on win
            }
        }

        logger.info("🎮 Minigames Manager initialized")

    def get_deposit_balance(self, wallet_address: str) -> dict:
        """Get user's available balance (merged deposits + winnings)"""
        try:
            # Get user's game balance record
            balance_result = self.supabase.table('minigame_balances')\
                .select('*')\
                .eq('wallet_address', wallet_address)\
                .execute()

            if balance_result.data:
                balance_data = balance_result.data[0]
                # Merge deposited_amount and available_winnings into single balance
                available_balance = balance_data.get('available_balance', 0)
                return {
                    'success': True,
                    'available_balance': available_balance,
                    'total_withdrawn': balance_data.get('total_withdrawn', 0),
                    'last_deposit_date': balance_data.get('last_deposit_date')
                }
            else:
                return {
                    'success': True,
                    'available_balance': 0,
                    'total_withdrawn': 0,
                    'last_deposit_date': None
                }

        except Exception as e:
            logger.error(f"❌ Error getting deposit balance: {e}")
            return {'success': False, 'error': str(e)}

    async def auto_verify_pending_deposits(self, wallet_address: str) -> dict:
        """
        Automatically verify pending deposits for a wallet
        Similar to P2P trading's automatic verification
        """
        try:
            logger.info(f"🔍 AUTO-VERIFY: Checking pending deposits for {wallet_address[:8]}...")
            
            # Get user's current balance
            balance_info = self.get_deposit_balance(wallet_address)
            today = date.today().isoformat()
            
            # Check blockchain for deposits
            deposits_result = await self.blockchain_service.check_pending_deposits(wallet_address)
            
            if not deposits_result.get('success'):
                return deposits_result
            
            deposits_found = deposits_result.get('deposits_found', [])
            
            if len(deposits_found) == 0:
                return {
                    'success': True,
                    'deposits_verified': 0,
                    'message': 'No pending deposits found'
                }
            
            # Get already recorded deposits
            recorded_deposits = self.supabase.table('minigame_deposits_log')\
                .select('tx_hash')\
                .eq('wallet_address', wallet_address)\
                .execute()
            
            recorded_tx_hashes = [d['tx_hash'] for d in (recorded_deposits.data or [])]
            
            # Process new deposits
            verified_count = 0
            total_new_amount = 0
            
            for deposit in deposits_found:
                tx_hash = deposit['tx_hash']
                amount = deposit['amount']
                
                # Skip if already recorded
                if tx_hash in recorded_tx_hashes:
                    logger.info(f"⏭️ Skipping already recorded deposit: {tx_hash[:16]}...")
                    continue
                
                # Check amount is within bounds
                if amount < self.MIN_DEPOSIT or amount > self.MAX_DEPOSIT:
                    logger.warning(f"⚠️ Deposit {tx_hash[:16]}... amount {amount} G$ out of bounds, skipping")
                    continue
                
                # Record the deposit
                try:
                    # Update or create balance record - add directly to available_balance
                    existing = self.supabase.table('minigame_balances')\
                        .select('*')\
                        .eq('wallet_address', wallet_address)\
                        .execute()
                    
                    if existing.data:
                        current = existing.data[0]
                        new_balance = current.get('available_balance', 0) + amount
                        
                        self.supabase.table('minigame_balances')\
                            .update({
                                'available_balance': new_balance,
                                'last_deposit_date': today,
                                'updated_at': datetime.now().isoformat()
                            })\
                            .eq('wallet_address', wallet_address)\
                            .execute()
                    else:
                        self.supabase.table('minigame_balances').insert({
                            'wallet_address': wallet_address,
                            'available_balance': amount,
                            'total_withdrawn': 0,
                            'last_deposit_date': today,
                            'created_at': datetime.now().isoformat()
                        }).execute()
                    
                    # Log the deposit
                    self.supabase.table('minigame_deposits_log').insert({
                        'wallet_address': wallet_address,
                        'amount': amount,
                        'tx_hash': tx_hash,
                        'deposit_date': today
                    }).execute()
                    
                    verified_count += 1
                    total_new_amount += amount
                    logger.info(f"✅ Auto-verified deposit: {amount} G$ (TX: {tx_hash[:16]}...)")
                    
                except Exception as record_error:
                    logger.error(f"❌ Error recording deposit {tx_hash[:16]}...: {record_error}")
                    continue
            
            return {
                'success': True,
                'deposits_verified': verified_count,
                'total_amount': total_new_amount,
                'message': f'Verified {verified_count} deposit(s) totaling {total_new_amount} G$'
            }
            
        except Exception as e:
            logger.error(f"❌ Error auto-verifying deposits: {e}")
            return {'success': False, 'error': str(e), 'deposits_verified': 0}

    def check_daily_limit(self, wallet_address: str, game_type: str) -> dict:
        """Check if user can play the game today"""
        try:
            today = date.today()

            limit_check = self.supabase.table('daily_game_limits')\
                .select('*')\
                .eq('wallet_address', wallet_address)\
                .eq('game_type', game_type)\
                .eq('game_date', today.isoformat())\
                .execute()

            max_plays = self.game_configs[game_type]['max_plays_per_day']

            if limit_check.data:
                plays_today = limit_check.data[0]['plays_today']
                can_play = plays_today < max_plays
                remaining = max(0, max_plays - plays_today)
            else:
                can_play = True
                plays_today = 0
                remaining = max_plays

            return {
                'can_play': can_play,
                'plays_today': plays_today,
                'remaining_plays': remaining,
                'max_plays': max_plays
            }

        except Exception as e:
            logger.error(f"❌ Error checking daily limit: {e}")
            return {'can_play': True, 'plays_today': 0, 'remaining_plays': 10, 'max_plays': 10}

    def start_game_session(self, wallet_address: str, game_type: str, bet_amount: float = 0) -> dict:
        """Start a new game session"""
        try:
            # Check daily limit
            limit_check = self.check_daily_limit(wallet_address, game_type)

            if not limit_check['can_play']:
                return {
                    'success': False,
                    'error': f"Daily limit reached (20 plays). Come back tomorrow!"
                }

            # For crash_game and coin_flip, validate and deduct bet amount
            if game_type == 'crash_game' or game_type == 'coin_flip':
                balance_info = self.get_deposit_balance(wallet_address)
                available_balance = balance_info.get('available_balance', 0)
                
                logger.info(f"💰 Balance check for {wallet_address[:8]}... - Available: {available_balance} G$, Bet: {bet_amount} G$")
                
                # Check if user has any balance
                if available_balance < 10:
                    logger.warning(f"❌ Insufficient balance: {available_balance} G$ < 10 G$ minimum")
                    return {
                        'success': False,
                        'error': f'No balance! You have {available_balance:.2f} G$. Please deposit at least 100 G$ to play.'
                    }
                
                # Validate bet amount
                config = self.game_configs[game_type]
                if bet_amount < config['min_bet']:
                    logger.warning(f"❌ Bet too low: {bet_amount} G$ < {config['min_bet']} G$ minimum")
                    return {
                        'success': False,
                        'error': f"Minimum bet is {config['min_bet']} G$"
                    }
                
                if bet_amount > config['max_bet']:
                    logger.warning(f"❌ Bet too high: {bet_amount} G$ > {config['max_bet']} G$ maximum")
                    return {
                        'success': False,
                        'error': f"Maximum bet is {config['max_bet']} G$"
                    }
                
                if bet_amount > available_balance:
                    logger.warning(f"❌ Insufficient funds: Bet {bet_amount} G$ > Available {available_balance} G$")
                    return {
                        'success': False,
                        'error': f'Insufficient balance! You have {available_balance:.2f} G$ but trying to bet {bet_amount:.2f} G$'
                    }
                
                # Deduct bet amount from available balance
                try:
                    new_balance_after_bet = available_balance - bet_amount
                    
                    logger.info(f"💰 BET DEDUCTION for {wallet_address[:8]}...")
                    logger.info(f"   Old balance: {available_balance} G$")
                    logger.info(f"   Bet amount: {bet_amount} G$")
                    logger.info(f"   New balance: {new_balance_after_bet} G$")
                    
                    self.supabase.table('minigame_balances')\
                        .update({
                            'available_balance': new_balance_after_bet,
                            'updated_at': datetime.now().isoformat()
                        })\
                        .eq('wallet_address', wallet_address)\
                        .execute()
                    
                    logger.info(f"✅ Successfully deducted bet {bet_amount} G$ from {wallet_address[:8]}... balance")
                except Exception as e:
                    logger.error(f"❌ Error deducting bet: {e}")
                    return {'success': False, 'error': 'Failed to process bet'}

            session_id = f"GAME-{uuid.uuid4().hex[:8].upper()}"

            session_data = {
                'session_id': session_id,
                'wallet_address': wallet_address,
                'game_type': game_type,
                'status': 'in_progress',
                'bet_amount': bet_amount if (game_type == 'crash_game' or game_type == 'coin_flip') else 0,
                'started_at': datetime.now().isoformat()
            }

            self.supabase.table('minigame_sessions').insert(session_data).execute()

            logger.info(f"🎮 Started {game_type} session {session_id} for {wallet_address[:8]}... (bet: {bet_amount} G$)")

            return {
                'success': True,
                'session_id': session_id,
                'game_type': game_type,
                'bet_amount': bet_amount,
                'config': self.game_configs[game_type]
            }

        except Exception as e:
            logger.error(f"❌ Error starting game session: {e}")
            return {'success': False, 'error': str(e)}

    async def complete_game_session(self, session_id: str, score: int, game_data: dict = None) -> dict:
        """Complete a game session and calculate rewards"""
        try:
            # Get session
            session = self.supabase.table('minigame_sessions')\
                .select('*')\
                .eq('session_id', session_id)\
                .execute()

            if not session.data:
                return {'success': False, 'error': 'Session not found'}

            session_info = session.data[0]
            wallet_address = session_info['wallet_address']
            game_type = session_info['game_type']

            # For crash_game and coin_flip, calculate winnings based on bet amount
            if game_type == 'crash_game' or game_type == 'coin_flip':
                bet_amount = session_info.get('bet_amount', 0)
                winnings = float(score)  # This is the total winnings (bet × multiplier) from frontend
                
                # If player lost (crashed without cashing out), refund nothing
                # If player won, winnings already calculated as bet × multiplier
                
                # Extract multiplier from game_data for score field (use integer version)
                multiplier_str = game_data.get('multiplier', '0.00') if game_data else '0.00'
                try:
                    multiplier_value = float(multiplier_str)
                    score_int = int(multiplier_value * 100)  # Store multiplier as integer (e.g., 1.69x = 169)
                except:
                    score_int = 0
                
                # Update session
                self.supabase.table('minigame_sessions')\
                    .update({
                        'score': score_int,
                        'g_dollar_earned': winnings,
                        'game_data': game_data or {},
                        'status': 'completed',
                        'completed_at': datetime.now().isoformat()
                    })\
                    .eq('session_id', session_id)\
                    .execute()

                # Update daily limits
                self._update_daily_limits(wallet_address, game_type, 0)

                # Add winnings to available balance
                balance_result = self.supabase.table('minigame_balances')\
                    .select('*')\
                    .eq('wallet_address', wallet_address)\
                    .execute()

                if balance_result.data:
                    current_balance = balance_result.data[0]
                    old_balance = current_balance.get('available_balance', 0)
                    new_balance = old_balance + winnings
                    
                    logger.info(f"💰 BALANCE UPDATE for {wallet_address[:8]}...")
                    logger.info(f"   Bet amount: {bet_amount} G$ (already deducted)")
                    logger.info(f"   Winnings to add: {winnings} G$")
                    logger.info(f"   Old balance: {old_balance} G$")
                    logger.info(f"   New balance: {new_balance} G$")
                    logger.info(f"   Net change: {winnings} G$")

                    self.supabase.table('minigame_balances')\
                        .update({
                            'available_balance': new_balance,
                            'updated_at': datetime.now().isoformat()
                        })\
                        .eq('wallet_address', wallet_address)\
                        .execute()

                    logger.info(f"✅ Game complete: {wallet_address[:8]}... won {winnings} G$")
                    logger.info(f"💰 New available balance: {new_balance} G$")

                    # Get updated limit info
                    limit_info = self.check_daily_limit(wallet_address, game_type)

                    return {
                        'success': True,
                        'score': score,
                        'winnings': winnings,
                        'available_balance': new_balance,
                        'can_withdraw': new_balance >= self.MIN_WITHDRAWAL,
                        'remaining_plays': limit_info.get('remaining_plays', 0),
                        'plays_today': limit_info.get('plays_today', 0),
                        'message': f'Won {winnings} G$! Total balance: {new_balance} G$'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No balance found. Please deposit G$ first to play.'
                    }

            else:
                # Other games: original instant reward logic
                reward_amount = self._calculate_reward(game_type, score, game_data)

                # Update session
                self.supabase.table('minigame_sessions')\
                    .update({
                        'score': score,
                        'g_dollar_earned': reward_amount,
                        'game_data': game_data or {},
                        'status': 'completed',
                        'completed_at': datetime.now().isoformat()
                    })\
                    .eq('session_id', session_id)\
                    .execute()

                # Update daily limits
                self._update_daily_limits(wallet_address, game_type, reward_amount)

                # Update user stats
                self._update_user_stats(wallet_address, game_type, score, reward_amount)

                # Disburse reward
                if reward_amount > 0:
                    disburse_result = await self.blockchain_service.disburse_game_reward(
                        wallet_address, reward_amount, game_type, session_id
                    )

                    if disburse_result['success']:
                        # Log reward
                        self.supabase.table('minigame_rewards_log').insert({
                            'transaction_hash': disburse_result['tx_hash'],
                            'wallet_address': wallet_address,
                            'game_type': game_type,
                            'session_id': session_id,
                            'reward_amount': reward_amount,
                            'score': score
                        }).execute()

                        return {
                            'success': True,
                            'score': score,
                            'reward': reward_amount,
                            'tx_hash': disburse_result['tx_hash'],
                            'explorer_url': disburse_result['explorer_url']
                        }
                    else:
                        return {
                            'success': False,
                            'error': disburse_result.get('error', 'Reward disbursement failed')
                        }
                else:
                    return {
                        'success': True,
                        'score': score,
                        'reward': 0,
                        'message': 'No reward earned'
                    }

        except Exception as e:
            logger.error(f"❌ Error completing game session: {e}")
            return {'success': False, 'error': str(e)}

    def _calculate_reward(self, game_type: str, score: int, game_data: dict = None) -> float:
        """Calculate reward based on game type and score"""
        config = self.game_configs[game_type]

        if game_type == 'catch_dollar':
            return score * config['reward_per_dollar']

        elif game_type == 'quiz_trivia':
            return score * config['reward_per_correct']

        elif game_type == 'battles':
            if game_data and game_data.get('won'):
                return config['stake_amount'] * config['reward_multiplier']
            return 0

        elif game_type == 'memory_card':
            matches = game_data.get('matches', 0) if game_data else 0
            return matches * config['reward_per_match']

        elif game_type == 'spin_wheel':
            return score  # Score is the reward itself

        return 0

    def _update_daily_limits(self, wallet_address: str, game_type: str, earned: float):
        """Update daily play limits"""
        try:
            today = date.today()

            existing = self.supabase.table('daily_game_limits')\
                .select('*')\
                .eq('wallet_address', wallet_address)\
                .eq('game_type', game_type)\
                .eq('game_date', today.isoformat())\
                .execute()

            if existing.data:
                self.supabase.table('daily_game_limits')\
                    .update({
                        'plays_today': existing.data[0]['plays_today'] + 1,
                        'earned_today': existing.data[0]['earned_today'] + earned
                    })\
                    .eq('id', existing.data[0]['id'])\
                    .execute()
            else:
                self.supabase.table('daily_game_limits').insert({
                    'wallet_address': wallet_address,
                    'game_date': today.isoformat(),
                    'game_type': game_type,
                    'plays_today': 1,
                    'earned_today': earned
                }).execute()

        except Exception as e:
            logger.error(f"❌ Error updating daily limits: {e}")

    def _update_user_stats(self, wallet_address: str, game_type: str, score: int, earned: float):
        """Update user game statistics"""
        try:
            existing = self.supabase.table('user_game_stats')\
                .select('*')\
                .eq('wallet_address', wallet_address)\
                .eq('game_type', game_type)\
                .execute()

            if existing.data:
                stats = existing.data[0]
                self.supabase.table('user_game_stats')\
                    .update({
                        'total_plays': stats['total_plays'] + 1,
                        'total_score': stats['total_score'] + score,
                        'highest_score': max(stats['highest_score'], score),
                        'total_earned': stats['total_earned'] + earned,
                        'virtual_tokens': stats.get('virtual_tokens', 0),  # Preserve existing tokens
                        'last_played': datetime.now().isoformat()
                    })\
                    .eq('id', stats['id'])\
                    .execute()
            else:
                self.supabase.table('user_game_stats').insert({
                    'wallet_address': wallet_address,
                    'game_type': game_type,
                    'total_plays': 1,
                    'total_score': score,
                    'highest_score': score,
                    'total_earned': earned,
                    'virtual_tokens': 0,  # Initialize with 0 tokens
                    'last_played': datetime.now().isoformat()
                }).execute()

        except Exception as e:
            logger.error(f"❌ Error updating user stats: {e}")

    def _update_user_stats_with_tokens(self, wallet_address: str, game_type: str, score: int, tokens_earned: int) -> dict:
        """Update user game statistics with virtual tokens"""
        try:
            existing = self.supabase.table('user_game_stats')\
                .select('*')\
                .eq('wallet_address', wallet_address)\
                .eq('game_type', game_type)\
                .execute()

            if existing.data:
                stats = existing.data[0]
                new_token_total = stats.get('virtual_tokens', 0) + tokens_earned

                result = self.supabase.table('user_game_stats')\
                    .update({
                        'total_plays': stats['total_plays'] + 1,
                        'total_score': stats['total_score'] + score,
                        'highest_score': max(stats['highest_score'], score),
                        'virtual_tokens': new_token_total,
                        'last_played': datetime.now().isoformat()
                    })\
                    .eq('id', stats['id'])\
                    .execute()

                logger.info(f"✅ Updated tokens: {stats.get('virtual_tokens', 0)} + {tokens_earned} = {new_token_total}")

                return {
                    'virtual_tokens': new_token_total,
                    'tokens_earned': tokens_earned,
                    'previous_tokens': stats.get('virtual_tokens', 0)
                }
            else:
                result = self.supabase.table('user_game_stats').insert({
                    'wallet_address': wallet_address,
                    'game_type': game_type,
                    'total_plays': 1,
                    'total_score': score,
                    'highest_score': score,
                    'total_earned': 0,
                    'virtual_tokens': tokens_earned,
                    'last_played': datetime.now().isoformat()
                }).execute()

                logger.info(f"✅ Created new stats with {tokens_earned} tokens")

                return {
                    'virtual_tokens': tokens_earned,
                    'tokens_earned': tokens_earned,
                    'previous_tokens': 0
                }

        except Exception as e:
            logger.error(f"❌ Error updating user stats with tokens: {e}")
            return {'virtual_tokens': 0, 'tokens_earned': 0, 'previous_tokens': 0}

    async def withdraw_winnings(self, wallet_address: str) -> dict:
        """Withdraw available balance"""
        try:
            # Get user's balance
            balance_result = self.supabase.table('minigame_balances')\
                .select('*')\
                .eq('wallet_address', wallet_address)\
                .execute()

            if not balance_result.data:
                return {'success': False, 'error': 'No balance found'}

            balance_data = balance_result.data[0]
            available_balance = balance_data.get('available_balance', 0)

            if available_balance <= 0:
                return {
                    'success': False,
                    'error': 'No balance available to withdraw'
                }
            
            # Check minimum withdrawal amount
            if available_balance < self.MIN_WITHDRAWAL:
                return {
                    'success': False,
                    'error': f'Minimum withdrawal is {self.MIN_WITHDRAWAL} G$. You have {available_balance} G$. Keep playing to reach the minimum!'
                }
            
            # Check maximum withdrawal amount
            if available_balance > self.MAX_WITHDRAWAL:
                return {
                    'success': False,
                    'error': f'Maximum withdrawal is {self.MAX_WITHDRAWAL} G$. You have {available_balance} G$. Please contact support for large withdrawals.'
                }

            # Disburse from GAMES_KEY
            session_id = f"WITHDRAW-{uuid.uuid4().hex[:8].upper()}"
            disburse_result = await self.blockchain_service.disburse_from_games_key(
                wallet_address, available_balance, session_id
            )

            # ONLY update balance if blockchain transaction was successful
            if disburse_result['success']:
                # Update balance - set to 0 and add to total withdrawn
                total_withdrawn = balance_data.get('total_withdrawn', 0) + available_balance

                self.supabase.table('minigame_balances')\
                    .update({
                        'available_balance': 0,
                        'total_withdrawn': total_withdrawn,
                        'updated_at': datetime.now().isoformat()
                    })\
                    .eq('wallet_address', wallet_address)\
                    .execute()

                # Log the withdrawal
                self.supabase.table('minigame_withdrawals_log').insert({
                    'wallet_address': wallet_address,
                    'amount': available_balance,
                    'tx_hash': disburse_result['tx_hash'],
                    'session_id': session_id,
                    'withdrawal_date': date.today().isoformat()
                }).execute()

                logger.info(f"✅ Balance withdrawn successfully: {available_balance} G$")

                return {
                    'success': True,
                    'amount_withdrawn': available_balance,
                    'tx_hash': disburse_result['tx_hash'],
                    'explorer_url': disburse_result['explorer_url'],
                    'message': f'Successfully withdrawn {available_balance} G$!'
                }
            else:
                # Withdrawal FAILED - balance NOT changed
                logger.error(f"❌ Blockchain withdrawal failed: {disburse_result.get('error')}")

                return {
                    'success': False,
                    'error': f"Withdrawal failed: {disburse_result.get('error', 'Unknown error')}. Your balance is safe.",
                    'balance_safe': True,
                    'available_balance': available_balance
                }

        except Exception as e:
            logger.error(f"❌ Error withdrawing balance: {e}")
            return {
                'success': False,
                'error': f'Withdrawal error: {str(e)}. Your balance is safe.',
                'balance_safe': True
            }

    def get_user_stats(self, wallet_address: str) -> dict:
        """Get user game statistics"""
        try:
            logger.info(f"🔍 Querying user_game_stats for {wallet_address[:8]}...")
            
            stats = self.supabase.table('user_game_stats')\
                .select('*')\
                .eq('wallet_address', wallet_address)\
                .execute()

            stats_data = stats.data or []
            logger.info(f"📊 Found {len(stats_data)} game records for {wallet_address[:8]}...")
            
            if stats_data:
                for stat in stats_data:
                    logger.info(f"   Game: {stat.get('game_type')}, Tokens: {stat.get('virtual_tokens', 0)}")

            return {
                'success': True,
                'stats': stats_data
            }

        except Exception as e:
            logger.error(f"❌ Error getting user stats: {e}")
            import traceback
            logger.error(f"🔍 Traceback: {traceback.format_exc()}")
            return {'success': True, 'error': str(e), 'stats': []}

    def get_quiz_questions(self, difficulty: str = None) -> list:
        """Get random quiz questions (using Learn & Earn schema)"""
        try:
            # Use Learn & Earn schema: question_id, question, answer_a, answer_b, answer_c, answer_d, correct
            query = self.supabase.table('quiz_questions').select('*')

            questions = query.execute()

            if questions.data:
                # Randomize and limit to 10
                random.shuffle(questions.data)
                quiz_questions = []

                for i, q in enumerate(questions.data[:10]):
                    quiz_questions.append({
                        'question_number': i + 1,
                        'question_id': q.get('question_id'),
                        'question': q.get('question'),
                        'options': [
                            q.get('answer_a'),
                            q.get('answer_b'),
                            q.get('answer_c'),
                            q.get('answer_d')
                        ],
                        'correct_answer': ord(q.get('correct', 'A')) - ord('A')  # Convert A,B,C,D to 0,1,2,3
                    })

                return quiz_questions

            return []

        except Exception as e:
            logger.error(f"❌ Error getting quiz questions: {e}")
            return []

# Global instance
minigames_manager = MinigamesManager()
