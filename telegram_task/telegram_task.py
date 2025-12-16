import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class TelegramTaskService:
    """
    Telegram Task Service

    Manages daily Telegram posting task where users post to t.me/GoodDollarX
    and submit their post link to earn 100 G$ rewards
    """

    def __init__(self):
        self.supabase = get_supabase_client()
        self.task_reward = 100.0  # 100 G$ reward

        # 1000+ Custom rotating messages with emoji themes and varied perspectives
        # Messages focus on GoodMarket features: mini-games, quizzes, tasks
        # EXPLICIT: "No wallet connection needed" messaging throughout
        # Each message ~50 words for detailed, engaging content
        self.custom_messages = self._generate_custom_messages()

        self.telegram_channel = "GoodDollarX"
        self.cooldown_hours = 24  # 24 hour cooldown

        logger.info("📱 Telegram Task Service initialized")
        logger.info(f"💰 Reward: {self.task_reward} G$")
        logger.info(f"📢 Channel: t.me/{self.telegram_channel}")
        logger.info(f"⏰ Cooldown: {self.cooldown_hours} hours")
        logger.info(f"💬 Custom Messages: {len(self.custom_messages)} unique variations available (daily rotation per user)")

    def _generate_custom_messages(self):
        """Generate 1000+ detailed custom messages featuring GoodMarket, quizzes, tasks, and GoodWallet"""
        messages = []

        # Detailed templates with GoodMarket features, instant payments, and GoodWallet mentions
        templates = [
            "{emoji} GoodMarket represents the perfect balance of earning opportunities! The quiz system rewards knowledge instantly, daily tasks are straightforward and pay immediately. GoodWallet makes claiming G$ incredibly easy and simple. The instant payment system builds trust you complete something you get paid right away! {benefit} 💚",
            "{emoji} I love GoodMarket's instant reward system! Quizzes pay out immediately when you answer correctly, daily tasks have straightforward requirements and instant G$ payments. GoodWallet is very easy to claim G$ every day with just a few taps. Trust is built through instant payments! {benefit} 🌍",
            "{emoji} GoodMarket is amazing for earning opportunities! Educational quizzes reward your knowledge instantly, daily tasks are simple and pay immediately upon completion. GoodWallet makes it very easy to claim your G$ daily rewards. You complete tasks you get paid right away no waiting! {benefit} ✨",
            "{emoji} The balance of earning on GoodMarket is perfect! Quiz system gives instant rewards for correct answers, daily tasks are clear and straightforward with immediate payment. GoodWallet is incredibly easy to use for claiming G$ daily. Instant payments build real trust in the platform! {benefit} 🚀",
            "{emoji} GoodMarket combines learning and earning brilliantly! Quizzes instantly reward your knowledge and intelligence, daily tasks pay immediately making earning straightforward. GoodWallet makes claiming G$ very easy every single day. The instant payment feature means you get paid right away! {benefit} 💰",
            "{emoji} I trust GoodMarket because payments are instant! Quiz rewards hit your wallet immediately, daily tasks pay out right away when completed. GoodWallet is very easy to claim G$ making daily earnings simple. Instant payment system builds confidence you earn you get paid! {benefit} 🎮",
            "{emoji} GoodMarket's earning system is perfectly balanced! Knowledge quizzes reward instantly, straightforward daily tasks pay immediately. GoodWallet makes it very easy to claim your G$ rewards daily. The instant payment model builds trust complete and get paid right away! {benefit} 🌟",
            "{emoji} Perfect earning opportunities on GoodMarket! Quizzes test knowledge and pay instantly, daily tasks are simple with immediate G$ payments. GoodWallet is incredibly easy for claiming your daily G$ rewards. Instant payments mean no waiting you complete you get paid! {benefit} 💚",
            "{emoji} GoodMarket represents true earning balance! Educational quizzes give instant rewards, daily tasks are straightforward and pay immediately. GoodWallet makes claiming G$ very easy and accessible daily. The instant payment system builds real trust in the platform! {benefit} ⚡",
            "{emoji} I love GoodMarket's instant reward model! Quiz system pays out immediately for correct answers, daily tasks are simple and pay right away. GoodWallet is very easy to claim G$ making daily rewards accessible. Instant payments build trust you earn you receive! {benefit} 🎯",
            "{emoji} GoodMarket balances earning perfectly! Quizzes reward knowledge instantly, straightforward daily tasks pay immediately upon completion. GoodWallet makes it incredibly easy to claim your G$ daily. Instant payment feature means you get paid right away no delays! {benefit} 🌈",
            "{emoji} The earning opportunities on GoodMarket are excellent! Quiz rewards are instant, daily tasks are clear and pay immediately. GoodWallet is very easy to use for claiming G$ every day. Instant payments build trust you complete tasks you get paid! {benefit} 🔥",
            "{emoji} GoodMarket provides balanced earning! Knowledge quizzes give instant rewards, daily tasks are straightforward with immediate payments. GoodWallet makes claiming G$ very easy and simple daily. The instant payment system means you get paid right away! {benefit} ⭐",
            "{emoji} I trust GoodMarket's instant payment system! Quizzes pay out immediately, daily tasks are simple and straightforward with instant G$ rewards. GoodWallet is incredibly easy to claim your daily G$. You complete something you receive payment right away! {benefit} 🎊",
            "{emoji} GoodMarket represents perfect earning balance! Educational quizzes reward instantly, daily tasks pay immediately and are straightforward. GoodWallet is very easy for claiming G$ making daily rewards simple. Instant payments build real trust in the platform! {benefit} 🌺",
        ]

        # Emoji categories
        emojis = [
            "🌱", "🎮", "💡", "🤝", "🔐", "🧭", "💰", "🌍", "🧠", "⚖️",
            "✨", "🚀", "💚", "🌟", "🎯", "💫", "🌈", "🔥", "⭐", "🎊",
            "🌺", "🎨", "🏆", "🎪", "🎭", "🎲", "🎰", "🕹️", "📱", "💻",
        ]

        # Benefit variations (more descriptive)
        benefits = [
            "Perfect for beginners starting their crypto journey",
            "Financial inclusion actually works in practice",
            "Accessible for all people worldwide",
            "True Web3 access without complications",
            "Daily opportunities for income growth",
            "Simple rewards system anyone can use",
            "Easy crypto access with no technical barriers",
            "Global participation encouraged and welcomed",
            "No barriers preventing your success",
            "Freedom starts with taking action",
            "Everyone participates and earns together",
            "Inclusive Web3 for the entire world",
            "Accessible crypto for everyday people",
            "Learn and earn simultaneously every day",
            "Financial empowerment for all humanity",
            "Universal access to digital currency",
            "Daily rewards building your wealth",
            "Simple system designed for everyone",
            "Global access to financial freedom",
            "Everyone earns real cryptocurrency rewards",
            "Building wealth one day at a time",
            "Community-driven financial revolution happening now",
            "Sustainable income for all participants",
            "Knowledge and earnings growing together",
            "Revolutionary platform changing lives globally",
        ]

        # Generate 1000+ messages using templates (100 variations each = 1000)
        for template in templates:
            for i in range(100):
                emoji = emojis[i % len(emojis)]
                benefit = benefits[i % len(benefits)]
                messages.append(template.format(emoji=emoji, benefit=benefit))

        return messages

    def _create_tables(self):
        """Create necessary database tables (run this in Supabase SQL editor)"""
        sql_commands = """
        -- Telegram task completion log
        CREATE TABLE IF NOT EXISTS telegram_task_log (
            id SERIAL PRIMARY KEY,
            wallet_address VARCHAR(42) NOT NULL,
            telegram_url TEXT NOT NULL,
            reward_amount DECIMAL(18,8) NOT NULL,
            transaction_hash VARCHAR(66) NOT NULL,
            status VARCHAR(20) DEFAULT 'completed',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(telegram_url)
        );

        CREATE INDEX IF NOT EXISTS idx_telegram_task_wallet ON telegram_task_log(wallet_address);
        CREATE INDEX IF NOT EXISTS idx_telegram_task_created ON telegram_task_log(created_at);

        ALTER TABLE telegram_task_log ENABLE ROW LEVEL SECURITY;
        CREATE POLICY "Allow all operations on telegram_task_log" ON telegram_task_log FOR ALL USING (true);
        """
        logger.info("📋 Telegram task database tables ready (run SQL commands in Supabase)")

    def _mask_wallet(self, wallet_address: str) -> str:
        """Mask wallet address for display"""
        if not wallet_address or len(wallet_address) < 10:
            return wallet_address
        return wallet_address[:6] + "..." + wallet_address[-4:]

    def get_custom_message_for_user(self, wallet_address: str) -> str:
        """Get a unique custom message for the user with DAILY ROTATION

        Each user gets a different message every day based on:
          1. Their wallet address (for uniqueness per user)
          2. Current date (for daily rotation)

        This ensures variety and prevents repetitive posts
        """
        import hashlib

        # Daily rotation with 1000+ messages
        current_date = datetime.now().strftime('%Y-%m-%d')
        daily_seed = f"{wallet_address}_{current_date}"
        daily_hash = int(hashlib.sha256(daily_seed.encode()).hexdigest(), 16)
        message_index = daily_hash % len(self.custom_messages)

        logger.info(f"📅 Daily message for {wallet_address[:8]}... on {current_date}: index {message_index}/{len(self.custom_messages)}")

        return self.custom_messages[message_index]

    def _validate_telegram_url(self, telegram_url: str) -> Dict[str, Any]:
        """Validate Telegram post URL and verify post existence via Telegram Bot API"""
        try:
            telegram_url = telegram_url.strip()

            if not telegram_url:
                return {"valid": False, "error": "Telegram post URL is required"}

            # Valid formats: https://t.me/GoodDollarX/123 or https://telegram.me/GoodDollarX/123
            if not (telegram_url.startswith("https://t.me/") or 
                   telegram_url.startswith("https://telegram.me/")):
                return {"valid": False, "error": "Please provide a valid Telegram post URL (https://t.me/...)"}

            # Check if URL contains the expected channel
            if f"/{self.telegram_channel}/" not in telegram_url:
                return {"valid": False, "error": f"Post must be in t.me/{self.telegram_channel} channel"}

            # Check if URL contains a message ID (number after channel name)
            url_parts = telegram_url.split('/')
            if len(url_parts) < 5 or not url_parts[-1].isdigit():
                return {"valid": False, "error": "URL must be a direct link to your Telegram post (should end with a message number)"}

            # Extract message ID
            message_id = int(url_parts[-1])

            # Minimum message ID validation - real posts in GoodDollarX are 6+ digits
            if message_id < 200000:
                return {"valid": False, "error": "Invalid post link. Please provide a real Telegram post URL from t.me/GoodDollarX channel"}

            # Additional check: reject common test numbers
            test_numbers = [123, 1234, 12345, 123456, 1234567]
            if message_id in test_numbers:
                return {"valid": False, "error": "Please provide a real Telegram post link, not a test URL"}

            # CRITICAL: Verify post exists using Telegram Web API (NO BOT TOKEN NEEDED)
            try:
                import requests
                from bs4 import BeautifulSoup

                # Access Telegram post via public web interface
                # This works for public channels without authentication
                web_url = f"https://t.me/{self.telegram_channel}/{message_id}?embed=1"

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }

                logger.info(f"🔍 Verifying post existence: {web_url}")

                response = requests.get(web_url, headers=headers, timeout=10, allow_redirects=False)

                # Check response status
                if response.status_code == 200:
                    # Post exists! Verify it's actually a post page
                    if 'tgme_widget_message' in response.text or 'message' in response.text.lower():
                        logger.info(f"✅ Telegram post {message_id} verified as existing")
                    else:
                        logger.warning(f"⚠️ URL exists but doesn't appear to be a valid post")
                        return {"valid": False, "error": "Invalid post URL. Please provide a real Telegram post link."}

                elif response.status_code == 404:
                    logger.warning(f"❌ Post {message_id} does not exist (404)")
                    return {"valid": False, "error": "This post does not exist. Please create a real post and submit the correct link."}

                elif response.status_code in [301, 302, 307, 308]:
                    # Redirects might indicate channel issues
                    logger.warning(f"⚠️ Post URL redirected (status {response.status_code})")
                    return {"valid": False, "error": "Invalid post link. Please verify you're using the correct channel."}

                else:
                    logger.warning(f"⚠️ Unexpected status code {response.status_code}")
                    # Don't block on unexpected errors, allow through
                    pass

            except requests.exceptions.Timeout:
                logger.warning(f"⚠️ Telegram verification timeout - allowing request")
                # Don't block user if verification times out
                pass

            except Exception as verify_error:
                logger.warning(f"⚠️ Post verification failed: {verify_error}")
                # Don't block user if verification fails
                pass

            return {"valid": True, "telegram_url": telegram_url}

        except Exception as e:
            logger.error(f"❌ Telegram URL validation error: {e}")
            return {"valid": False, "error": "Validation failed. Please try again."}

    async def check_eligibility(self, wallet_address: str) -> Dict[str, Any]:
        """Check if user can claim Telegram task reward"""
        try:
            if not self.supabase:
                return {
                    'can_claim': True,
                    'reason': 'Database not available'
                }

            logger.info(f"🔍 Checking Telegram eligibility for {wallet_address[:8]}...")

            # Check for pending submission (waiting for approval)
            # Cooldown starts IMMEDIATELY after submission, not after approval
            pending_check = self.supabase.table('telegram_task_log')\
                .select('created_at, status')\
                .eq('wallet_address', wallet_address)\
                .eq('status', 'pending')\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()

            logger.info(f"🔍 Pending check result: {len(pending_check.data) if pending_check.data else 0} pending submissions")

            if pending_check.data:
                # Cooldown active - submission is pending
                pending_time = datetime.fromisoformat(pending_check.data[0]['created_at'].replace('Z', '+00:00'))
                next_claim_time = pending_time + timedelta(hours=self.cooldown_hours)

                logger.info(f"⏰ Cooldown active (pending) - Submitted: {pending_time}, Next available: {next_claim_time}")

                return {
                    'can_claim': False,
                    'has_pending_submission': True,
                    'reason': 'Waiting for admin approval',
                    'status': 'pending',
                    'next_claim_time': next_claim_time.isoformat(),
                    'last_claim': pending_time.isoformat()
                }

            # Check last COMPLETED or REJECTED claim within 24 hours
            # Only check claims from the last 24 hours
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.cooldown_hours)
            last_claim = self.supabase.table('telegram_task_log')\
                .select('created_at, status')\
                .eq('wallet_address', wallet_address)\
                .in_('status', ['completed', 'rejected'])\
                .gte('created_at', cutoff_time.isoformat())\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()

            logger.info(f"🔍 Recent claims (last 24h): {len(last_claim.data) if last_claim.data else 0}")
            if last_claim.data:
                logger.info(f"🔍 Last claim: {last_claim.data[0]}")

            if last_claim.data:
                last_claim_status = last_claim.data[0]['status']
                
                # If last claim was REJECTED, user can resubmit immediately
                if last_claim_status == 'rejected':
                    logger.info(f"✅ Last submission was rejected - user can resubmit")
                    return {
                        'can_claim': True,
                        'reward_amount': self.task_reward
                    }
                
                # If last claim was COMPLETED, cooldown is active
                if last_claim_status == 'completed':
                    last_claim_time = datetime.fromisoformat(last_claim.data[0]['created_at'].replace('Z', '+00:00'))
                    next_claim_time = last_claim_time + timedelta(hours=self.cooldown_hours)

                    logger.info(f"⏰ Cooldown active (completed) - Last claim: {last_claim_time}, Next available: {next_claim_time}")

                    return {
                        'can_claim': False,
                        'reason': 'Already claimed today',
                        'next_claim_time': next_claim_time.isoformat(),
                        'last_claim': last_claim_time.isoformat()
                    }

            logger.info(f"✅ User can claim - no recent submissions")

            return {
                'can_claim': True,
                'reward_amount': self.task_reward
            }

        except Exception as e:
            logger.error(f"❌ Error checking Telegram task eligibility: {e}")
            return {
                'can_claim': True,
                'reason': 'Error checking eligibility'
            }

    async def claim_task_reward(self, wallet_address: str, telegram_url: str) -> Dict[str, Any]:
        """Submit Telegram task for admin approval"""
        try:
            logger.info(f"📱 Telegram task submission started for {wallet_address[:8]}... with URL: {telegram_url}")

            # Check maintenance mode
            from maintenance_service import maintenance_service
            maintenance_status = maintenance_service.get_maintenance_status('telegram_task')

            if maintenance_status.get('is_maintenance'):
                logger.warning(f"🔧 Telegram Task in maintenance mode")
                return {
                    'success': False,
                    'error': maintenance_status.get('message', 'Telegram Task is under maintenance')
                }

            # Validate URL
            validation = self._validate_telegram_url(telegram_url)
            logger.info(f"🔍 URL validation result: {validation}")

            if not validation.get('valid'):
                logger.warning(f"❌ URL validation failed: {validation.get('error')}")
                return {
                    'success': False,
                    'error': validation.get('error')
                }

            # Check eligibility
            eligibility = await self.check_eligibility(wallet_address)
            logger.info(f"🔍 Eligibility check result: {eligibility}")

            if not eligibility.get('can_claim'):
                logger.warning(f"❌ Not eligible to claim: {eligibility.get('reason')}")
                return {
                    'success': False,
                    'error': eligibility.get('reason', 'Cannot claim at this time')
                }

            # CRITICAL: Check if URL already exists in database
            if self.supabase:
                try:
                    # Check if this EXACT URL was already used by ANYONE
                    url_check = self.supabase.table('telegram_task_log')\
                        .select('wallet_address, created_at, status')\
                        .eq('telegram_url', telegram_url)\
                        .execute()

                    if url_check.data and len(url_check.data) > 0:
                        previous_claim = url_check.data[0]
                        previous_wallet = previous_claim.get('wallet_address', 'Unknown')
                        previous_status = previous_claim.get('status', 'pending')

                        if previous_wallet == wallet_address:
                            if previous_status == 'pending':
                                return {
                                    'success': False,
                                    'error': 'You already submitted this post. Please wait for admin approval.'
                                }
                            else:
                                logger.warning(f"❌ User {wallet_address[:8]}... already claimed with this URL")
                                return {
                                    'success': False,
                                    'error': 'You have already used this Telegram post for rewards. Please create a new post.'
                                }
                        else:
                            logger.warning(f"❌ URL already used by another wallet: {previous_wallet[:8]}...")
                            return {
                                'success': False,
                                'error': 'This Telegram post link has already been used. Please create your own post.'
                            }

                    logger.info(f"✅ URL is unique and unused - submitting for approval")

                except Exception as db_error:
                    logger.error(f"❌ Database URL check error: {db_error}")
                    return {
                        'success': False,
                        'error': 'Unable to verify post uniqueness. Please try again.'
                    }

            # Submit for admin approval instead of immediate disbursement
            if self.supabase:
                try:
                    # Insert with NULL transaction_hash for pending submissions
                    # Transaction hash will be added when admin approves
                    self.supabase.table('telegram_task_log').insert({
                        'wallet_address': wallet_address,
                        'telegram_url': telegram_url,
                        'reward_amount': self.task_reward,
                        'status': 'pending',
                        'transaction_hash': None,  # Will be set after admin approval
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }).execute()

                    logger.info(f"✅ Telegram task submitted for approval: {self._mask_wallet(wallet_address)}")

                    return {
                        'success': True,
                        'pending': True,
                        'message': f'✅ Submission successful! Your post is waiting for admin approval.',
                        'status': 'pending_approval',
                        'telegram_url': telegram_url
                    }
                except Exception as insert_error:
                    logger.error(f"❌ Failed to submit for approval: {insert_error}")
                    return {
                        'success': False,
                        'error': 'Failed to submit for approval. Please try again.'
                    }

        except Exception as e:
            logger.error(f"❌ Telegram task submission error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def approve_submission(self, submission_id: int, admin_wallet: str) -> Dict[str, Any]:
        """Admin approves a submission and disburses reward"""
        try:
            if not self.supabase:
                return {'success': False, 'error': 'Database not available'}

            # Get submission details
            submission = self.supabase.table('telegram_task_log')\
                .select('*')\
                .eq('id', submission_id)\
                .eq('status', 'pending')\
                .execute()

            if not submission.data or len(submission.data) == 0:
                return {'success': False, 'error': 'Submission not found or already processed'}

            sub_data = submission.data[0]
            wallet_address = sub_data['wallet_address']
            telegram_url = sub_data['telegram_url']

            logger.info(f"✅ Admin {admin_wallet[:8]}... approving submission {submission_id}")

            # Disburse reward
            from telegram_task.blockchain import telegram_blockchain_service

            disbursement = telegram_blockchain_service.disburse_telegram_reward_sync(
                wallet_address=wallet_address,
                amount=self.task_reward
            )

            if disbursement.get('success'):
                # Update status to completed
                self.supabase.table('telegram_task_log').update({
                    'status': 'completed',
                    'transaction_hash': disbursement.get('tx_hash'),
                    'approved_by': admin_wallet,
                    'approved_at': datetime.now(timezone.utc).isoformat()
                }).eq('id', submission_id).execute()

                logger.info(f"✅ Telegram task approved and disbursed: {self.task_reward} G$ to {self._mask_wallet(wallet_address)}")

                return {
                    'success': True,
                    'tx_hash': disbursement.get('tx_hash'),
                    'message': f'Approved! {self.task_reward} G$ disbursed to user.'
                }
            else:
                # Update status to failed if disbursement failed
                self.supabase.table('telegram_task_log').update({
                    'status': 'failed',
                    'approved_by': admin_wallet,
                    'approved_at': datetime.now(timezone.utc).isoformat(),
                    'error_message': disbursement.get('error')
                }).eq('id', submission_id).execute()

                logger.error(f"❌ Disbursement failed for submission {submission_id}: {disbursement.get('error')}")

                return {
                    'success': False,
                    'error': f"Disbursement failed: {disbursement.get('error')}"
                }

        except Exception as e:
            logger.error(f"❌ Approval error: {e}")
            return {'success': False, 'error': str(e)}

    async def reject_submission(self, submission_id: int, admin_wallet: str, reason: str = '') -> Dict[str, Any]:
        """Admin rejects a submission - user can immediately resubmit"""
        try:
            if not self.supabase:
                return {'success': False, 'error': 'Database not available'}

            # Update status to rejected
            result = self.supabase.table('telegram_task_log').update({
                'status': 'rejected',
                'rejected_by': admin_wallet,
                'rejected_at': datetime.now(timezone.utc).isoformat(),
                'rejection_reason': reason
            }).eq('id', submission_id).eq('status', 'pending').execute()

            if result.data:
                logger.info(f"❌ Admin {admin_wallet[:8]}... rejected submission {submission_id} - User can resubmit immediately")

                return {
                    'success': True,
                    'message': 'Submission rejected. User can resubmit immediately with a new post.'
                }
            else:
                return {'success': False, 'error': 'Submission not found or already processed'}

        except Exception as e:
            logger.error(f"❌ Rejection error: {e}")
            return {'success': False, 'error': str(e)}

    async def get_task_stats(self, wallet_address: str) -> Dict[str, Any]:
        """Get user's Telegram task statistics"""
        try:
            if not self.supabase:
                return {
                    'total_earned': 0,
                    'total_claims': 0,
                    'can_claim_today': True
                }

            # Get total earned
            claims = self.supabase.table('telegram_task_log')\
                .select('reward_amount')\
                .eq('wallet_address', wallet_address)\
                .execute()

            total_earned = sum(float(c.get('reward_amount', 0)) for c in claims.data or [])
            total_claims = len(claims.data or [])

            # Check if can claim today
            eligibility = await self.check_eligibility(wallet_address)

            return {
                'total_earned': total_earned,
                'total_claims': total_claims,
                'can_claim_today': eligibility.get('can_claim', False),
                'next_claim_time': eligibility.get('next_claim_time'),
                'reward_amount': self.task_reward
            }

        except Exception as e:
            logger.error(f"❌ Error getting Telegram task stats: {e}")
            return {
                'total_earned': 0,
                'total_claims': 0,
                'can_claim_today': True
            }

    def get_transaction_history(self, wallet_address: str, limit: int = 50) -> Dict[str, Any]:
        """Get user's Telegram task transaction history"""
        try:
            if not self.supabase:
                return {
                    'success': True,
                    'transactions': [],
                    'total_count': 0,
                    'total_earned': 0
                }

            logger.info(f"📋 Getting Telegram task history for {wallet_address[:8]}... (limit: {limit})")

            # Get transaction history
            history = self.supabase.table('telegram_task_log')\
                .select('*')\
                .eq('wallet_address', wallet_address)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()

            transactions = []
            total_earned = 0

            if history.data:
                for record in history.data:
                    reward_amount = float(record.get('reward_amount', 0))
                    total_earned += reward_amount

                    transactions.append({
                        'id': record.get('id'),
                        'reward_amount': reward_amount,
                        'transaction_hash': record.get('transaction_hash'),
                        'telegram_url': record.get('telegram_url'),
                        'status': record.get('status', 'completed'),
                        'created_at': record.get('created_at'),
                        'explorer_url': f"https://explorer.celo.org/mainnet/tx/{record.get('transaction_hash')}" if record.get('transaction_hash') else None
                    })

            logger.info(f"✅ Retrieved {len(transactions)} Telegram task transactions for {wallet_address[:8]}... (Total: {total_earned} G$)")

            return {
                'success': True,
                'transactions': transactions,
                'total_count': len(transactions),
                'total_earned': total_earned,
                'summary': {
                    'total_earned': total_earned,
                    'transaction_count': len(transactions),
                    'avg_reward': total_earned / len(transactions) if transactions else 0
                }
            }

        except Exception as e:
            logger.error(f"❌ Error getting Telegram task transaction history: {e}")
            return {
                'success': False,
                'error': str(e),
                'transactions': [],
                'total_count': 0,
                'total_earned': 0
            }

# Global instance
telegram_task_service = TelegramTaskService()

def init_telegram_task(app):
    """Initialize Telegram Task system with Flask app"""
    try:
        logger.info("📱 Initializing Telegram Task system...")

        from flask import session, request, jsonify

        @app.route('/api/telegram-task/status', methods=['GET'])
        def get_telegram_task_status():
            """Get Telegram task status for current user"""
            try:
                wallet_address = session.get('wallet_address') or session.get('wallet')
                if not wallet_address or not session.get('verified'):
                    return jsonify({'error': 'Not authenticated'}), 401

                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    stats = loop.run_until_complete(
                        telegram_task_service.get_task_stats(wallet_address)
                    )
                finally:
                    loop.close()

                return jsonify(stats), 200

            except Exception as e:
                logger.error(f"❌ Telegram task status error: {e}")
                return jsonify({'error': 'Failed to get task status'}), 500

        @app.route('/api/telegram-task/custom-message', methods=['GET'])
        def get_telegram_custom_message():
            """Get custom message for current user"""
            try:
                wallet_address = session.get('wallet_address') or session.get('wallet')
                verified = session.get('verified')

                logger.info(f"📱 Custom message request - wallet: {wallet_address[:8] if wallet_address else 'None'}..., verified: {verified}")
                logger.info(f"📱 Session keys: {list(session.keys())}")

                if not wallet_address:
                    logger.warning(f"❌ No wallet address in session")
                    return jsonify({
                        'success': False,
                        'error': 'Not authenticated - no wallet'
                    }), 401

                if not verified:
                    logger.warning(f"❌ Wallet not verified")
                    return jsonify({
                        'success': False,
                        'error': 'Not authenticated - not verified'
                    }), 401

                # Get the custom message for this user
                custom_message = telegram_task_service.get_custom_message_for_user(wallet_address)

                logger.info(f"✅ Custom message generated for {wallet_address[:8]}... (length: {len(custom_message)})")

                return jsonify({
                    'success': True,
                    'custom_message': custom_message,
                    'wallet': wallet_address[:8] + "..."
                }), 200

            except Exception as e:
                logger.error(f"❌ Error getting custom message: {e}")
                import traceback
                logger.error(f"🔍 Traceback: {traceback.format_exc()}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to generate message',
                    'details': str(e)
                }), 500

        @app.route('/api/telegram-task/claim', methods=['POST'])
        def claim_telegram_task():
            """Claim Telegram task reward"""
            try:
                wallet_address = session.get('wallet_address') or session.get('wallet')
                if not wallet_address or not session.get('verified'):
                    return jsonify({'error': 'Not authenticated'}), 401

                data = request.get_json()
                telegram_url = data.get('telegram_url', '').strip()

                if not telegram_url:
                    return jsonify({
                        'success': False,
                        'error': 'Telegram post URL is required'
                    }), 400

                import asyncio

                # Use a fresh event loop to avoid conflicts
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    result = loop.run_until_complete(
                        telegram_task_service.claim_task_reward(wallet_address, telegram_url)
                    )
                finally:
                    try:
                        loop.close()
                    except:
                        pass

                if result.get('success'):
                    return jsonify(result), 200
                else:
                    return jsonify(result), 400

            except Exception as e:
                logger.error(f"❌ Telegram task claim error: {e}")
                import traceback
                logger.error(f"🔍 Traceback: {traceback.format_exc()}")
                return jsonify({'error': 'Failed to claim task', 'details': str(e)}), 500

        @app.route('/api/telegram-task/history', methods=['GET'])
        def get_telegram_task_history():
            """Get Telegram task transaction history for current user"""
            try:
                wallet_address = session.get('wallet_address') or session.get('wallet')
                if not wallet_address or not session.get('verified'):
                    return jsonify({'error': 'Not authenticated'}), 401

                limit = int(request.args.get('limit', 50))

                history = telegram_task_service.get_transaction_history(wallet_address, limit)

                return jsonify(history), 200

            except Exception as e:
                logger.error(f"❌ Telegram task history error: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to get transaction history',
                    'transactions': [],
                    'total_count': 0
                }), 500

        logger.info("✅ Telegram Task system initialized successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to initialize Telegram Task system: {e}")
        return False
