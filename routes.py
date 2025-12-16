from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from blockchain import has_recent_ubi_claim, GOODDOLLAR_CONTRACTS
from analytics_service import analytics
from supabase_client import get_supabase_client, safe_supabase_operation, supabase_logger, log_admin_action
import json
import logging
import os

# Logger for this module
logger = logging.getLogger(__name__)

# Create Blueprint FIRST - BEFORE any route decorators
routes = Blueprint("routes", __name__)

def auth_required(f):
    """Decorator for endpoints requiring authentication with auto-logout on expiry"""
    def wrapper(*args, **kwargs):
        wallet = session.get("wallet")
        verified = session.get("verified")

        if not verified or not wallet:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        # Check if UBI claim is still valid (recent within 24 hours)
        from blockchain import has_recent_ubi_claim
        ubi_check = has_recent_ubi_claim(wallet)

        if ubi_check["status"] != "success":
            # UBI claim expired - auto logout
            logger.warning(f"⚠️ Auto-logout: UBI verification expired for {wallet[:8]}...")
            session.clear()
            return jsonify({
                "success": False,
                "error": "Session expired. Please log in again.",
                "auto_logout": True,
                "redirect": "/"
            }), 401

        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def admin_required(f):
    """Decorator for endpoints requiring admin authentication"""
    def wrapper(*args, **kwargs):
        wallet = session.get("wallet")
        if not session.get("verified") or not wallet:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        from supabase_client import is_admin
        if not is_admin(wallet):
            return jsonify({"success": False, "error": "Admin access required"}), 403

        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@routes.route('/api/daily-task/status', methods=['GET'])
@auth_required
def get_daily_task_status():
    """Get unified daily task status (checks both Twitter and Telegram)"""
    try:
        wallet = session.get('wallet')

        # Import both services
        from twitter_task.twitter_task import twitter_task_service
        from telegram_task.telegram_task import telegram_task_service
        from datetime import datetime, timezone

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Check both tasks
            twitter_status = loop.run_until_complete(twitter_task_service.check_eligibility(wallet))
            telegram_status = loop.run_until_complete(telegram_task_service.check_eligibility(wallet))

            # Check for pending submissions
            has_pending_telegram = telegram_status.get('has_pending_submission', False)
            has_pending_twitter = twitter_status.get('has_pending_submission', False)
            has_pending = has_pending_telegram or has_pending_twitter

            # User can claim if BOTH are available (shared cooldown) and no pending submissions
            can_claim = twitter_status.get('can_claim', False) and telegram_status.get('can_claim', False) and not has_pending

            # Get next claim time from whichever was claimed more recently
            next_claim_time = None
            time_remaining_seconds = None
            if not can_claim:
                twitter_next = twitter_status.get('next_claim_time')
                telegram_next = telegram_status.get('next_claim_time')

                # Use the later time (whichever task was done more recently)
                if twitter_next and telegram_next:
                    next_claim_time = max(twitter_next, telegram_next)
                else:
                    next_claim_time = twitter_next or telegram_next

                # Calculate time_remaining_seconds for live countdown timer
                if next_claim_time:
                    try:
                        next_claim_dt = datetime.fromisoformat(next_claim_time.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        time_remaining_seconds = max(0, int((next_claim_dt - now).total_seconds()))
                    except Exception as e:
                        logger.error(f"❌ Error calculating time remaining: {e}")
                        time_remaining_seconds = 0

            # Determine pending platform
            pending_platform = None
            if has_pending_twitter:
                pending_platform = 'Twitter'
            elif has_pending_telegram:
                pending_platform = 'Telegram'

            return jsonify({
                'can_claim': can_claim,
                'has_pending_submission': has_pending,
                'pending_platform': pending_platform,
                'next_claim_time': next_claim_time,
                'time_remaining_seconds': time_remaining_seconds
            }), 200
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"❌ Daily task status error: {e}")
        return jsonify({'error': 'Failed to get task status'}), 500

@routes.route('/api/daily-task/claim', methods=['POST'])
@auth_required
def claim_daily_task():
    """Unified endpoint for claiming both Telegram and Twitter tasks"""
    try:
        wallet = session.get('wallet')
        data = request.get_json()
        platform = data.get('platform', '').lower()
        post_url = data.get('post_url', '').strip()

        if not platform or platform not in ['telegram', 'twitter']:
            return jsonify({'success': False, 'error': 'Invalid platform'}), 400

        if not post_url:
            return jsonify({'success': False, 'error': 'Post URL is required'}), 400

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            if platform == 'telegram':
                from telegram_task.telegram_task import telegram_task_service
                result = loop.run_until_complete(
                    telegram_task_service.claim_task_reward(wallet, post_url)
                )
            else:
                from twitter_task.twitter_task import twitter_task_service
                result = loop.run_until_complete(
                    twitter_task_service.claim_task_reward(wallet, post_url)
                )

            if result.get('success'):
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        finally:
            try:
                loop.close()
            except:
                pass

    except Exception as e:
        logger.error(f"❌ Daily task claim error: {e}")
        import traceback
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': 'Failed to claim reward'}), 500

@routes.route('/api/daily-task/history', methods=['GET'])
@auth_required
def get_daily_task_history():
    """Get combined Twitter and Telegram task history"""
    try:
        wallet = session.get('wallet')
        limit = int(request.args.get('limit', 50))

        from twitter_task.twitter_task import twitter_task_service
        from telegram_task.telegram_task import telegram_task_service

        # Get both histories
        twitter_history = twitter_task_service.get_transaction_history(wallet, limit)
        telegram_history = telegram_task_service.get_transaction_history(wallet, limit)

        # Combine transactions
        all_transactions = []

        if twitter_history.get('success') and twitter_history.get('transactions'):
            for tx in twitter_history['transactions']:
                tx['platform'] = 'twitter'
                all_transactions.append(tx)

        if telegram_history.get('success') and telegram_history.get('transactions'):
            for tx in telegram_history['transactions']:
                tx['platform'] = 'telegram'
                all_transactions.append(tx)

        # Sort by date (newest first)
        all_transactions.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        # Limit results
        all_transactions = all_transactions[:limit]

        # Calculate totals
        total_earned = sum(float(tx.get('reward_amount', 0)) for tx in all_transactions)

        return jsonify({
            'success': True,
            'transactions': all_transactions,
            'total_count': len(all_transactions),
            'total_earned': total_earned
        })

    except Exception as e:
        logger.error(f"❌ Daily task history error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get history',
            'transactions': [],
            'total_count': 0,
            'total_earned': 0
        }), 500

@routes.route("/api/can-edit-username", methods=["GET"])
@auth_required
def can_edit_username():
    """Check if user can edit their username"""
    try:
        wallet = session.get("wallet")
        supabase = get_supabase_client()

        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Check if user has already edited username
        user_result = safe_supabase_operation(
            lambda: supabase.table('user_data').select('username, username_edited').eq('wallet_address', wallet).execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="check username edit status"
        )

        can_edit = True
        if user_result.data and len(user_result.data) > 0:
            user_data = user_result.data[0]
            username_edited = user_data.get('username_edited', False)
            can_edit = not username_edited

        return jsonify({
            "success": True,
            "can_edit": can_edit
        })

    except Exception as e:
        logger.error(f"❌ Error checking username edit status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/edit-username", methods=["POST"])
@auth_required
def edit_username():
    """Edit username (one-time only)"""
    try:
        wallet = session.get("wallet")
        data = request.get_json()
        new_username = data.get("username", "").strip()

        if not new_username:
            return jsonify({"success": False, "error": "Username is required"}), 400

        # Validate username
        if len(new_username) < 3 or len(new_username) > 20:
            return jsonify({"success": False, "error": "Username must be 3-20 characters"}), 400

        if not new_username.replace('_', '').isalnum():
            return jsonify({"success": False, "error": "Username can only contain letters, numbers, and underscores"}), 400

        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Check if username is already taken
        username_check = safe_supabase_operation(
            lambda: supabase.table('user_data').select('wallet_address').eq('username', new_username).execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="check username availability"
        )

        if username_check.data and len(username_check.data) > 0:
            existing_wallet = username_check.data[0].get('wallet_address')
            if existing_wallet != wallet:
                return jsonify({"success": False, "error": "Username already taken"}), 400

        # Check if user can edit
        user_result = safe_supabase_operation(
            lambda: supabase.table('user_data').select('username_edited').eq('wallet_address', wallet).execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="check edit permission"
        )

        if user_result.data and len(user_result.data) > 0:
            username_edited = user_result.data[0].get('username_edited', False)
            if username_edited:
                return jsonify({"success": False, "error": "Username can only be edited once"}), 400

        # Update username and mark as edited
        update_result = safe_supabase_operation(
            lambda: supabase.table('user_data').update({
                'username': new_username,
                'username_edited': True
            }).eq('wallet_address', wallet).execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="update username"
        )

        if not update_result.data:
            return jsonify({"success": False, "error": "Failed to update username"}), 500

        # Update session
        session['username'] = new_username

        logger.info(f"✅ Username updated to {new_username} for {wallet[:8]}...")

        return jsonify({
            "success": True,
            "message": "Username updated successfully!",
            "username": new_username
        })

    except Exception as e:
        logger.error(f"❌ Error editing username: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/recent-daily-tasks", methods=["GET"])
def get_recent_daily_tasks():
    """Get recent daily task submissions from last 24 hours"""
    try:
        from datetime import datetime, timedelta
        from supabase_client import get_supabase_client
        from flask import Response

        supabase = get_supabase_client()
        if not supabase:
            response = jsonify({"success": False, "submissions": []})
            response.headers['Content-Type'] = 'application/json'
            return response, 200

        # Calculate 24 hours ago
        twenty_four_hours_ago = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        # Get Twitter task submissions from last 24 hours
        twitter_submissions = safe_supabase_operation(
            lambda: supabase.table('twitter_task_log')\
                .select('wallet_address, reward_amount, created_at, twitter_url')\
                .gte('created_at', twenty_four_hours_ago)\
                .order('created_at', desc=True)\
                .limit(50)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get recent twitter tasks"
        )

        # Get Telegram task submissions from last 24 hours
        telegram_submissions = safe_supabase_operation(
            lambda: supabase.table('telegram_task_log')\
                .select('wallet_address, reward_amount, created_at, telegram_url')\
                .gte('created_at', twenty_four_hours_ago)\
                .order('created_at', desc=True)\
                .limit(50)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get recent telegram tasks"
        )

        # Combine and format submissions WITH MESSAGES/LINKS
        all_submissions = []

        # Add Twitter submissions WITH LINKS
        if twitter_submissions and twitter_submissions.data:
            for sub in twitter_submissions.data:
                wallet = sub.get('wallet_address', '')
                username = supabase_logger.get_username(wallet)

                all_submissions.append({
                    'wallet_address': wallet,
                    'display_name': username if username else f"{wallet[:6]}...{wallet[-4:]}",
                    'reward_amount': float(sub.get('reward_amount', 0)),
                    'created_at': sub.get('created_at'),
                    'platform': 'Twitter',
                    'submission_url': sub.get('twitter_url', ''),  # ADD TWITTER URL
                    'submission_type': 'twitter_post'
                })

        # Add Telegram submissions WITH LINKS
        if telegram_submissions and telegram_submissions.data:
            for sub in telegram_submissions.data:
                wallet = sub.get('wallet_address', '')
                username = supabase_logger.get_username(wallet)

                all_submissions.append({
                    'wallet_address': wallet,
                    'display_name': username if username else f"{wallet[:6]}...{wallet[-4:]}",
                    'reward_amount': float(sub.get('reward_amount', 0)),
                    'created_at': sub.get('created_at'),
                    'platform': 'Telegram',
                    'submission_url': sub.get('telegram_url', ''),  # ADD TELEGRAM URL
                    'submission_type': 'telegram_post'
                })


        # Sort by created_at (newest first)
        all_submissions.sort(key=lambda x: x['created_at'], reverse=True)

        # Limit to 20 most recent
        all_submissions = all_submissions[:20]

        logger.info(f"✅ Returning {len(all_submissions)} recent daily task submissions")

        response = jsonify({
            "success": True,
            "submissions": all_submissions,
            "total_count": len(all_submissions)
        })
        response.headers['Content-Type'] = 'application/json'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response, 200

    except Exception as e:
        logger.error(f"❌ Error getting recent daily tasks: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        error_response = jsonify({"success": False, "submissions": [], "error": str(e)})
        error_response.headers['Content-Type'] = 'application/json'
        return error_response, 200

@routes.route("/api/learn-earn-participants", methods=["GET"])
def get_learn_earn_participants():
    """Get Learn & Earn participants for a specific date or date range"""
    try:
        from datetime import datetime
        from supabase_client import get_supabase_client

        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "participants": []})

        # Get date parameter (format: YYYY-MM-DD)
        target_date = request.args.get('date')

        if target_date:
            # Query for specific date
            start_datetime = f"{target_date} 00:00:00"
            end_datetime = f"{target_date} 23:59:59"
        else:
            # Default to today
            today = datetime.utcnow().strftime('%Y-%m-%d')
            start_datetime = f"{today} 00:00:00"
            end_datetime = f"{today} 23:59:59"

        # Get all Learn & Earn participants for the date
        participants = safe_supabase_operation(
            lambda: supabase.table('learnearn_log')\
                .select('wallet_address, amount_g$, timestamp, transaction_hash, quiz_id')\
                .gte('timestamp', start_datetime)\
                .lte('timestamp', end_datetime)\
                .eq('status', True)\
                .order('timestamp', desc=True)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get learn earn participants"
        )

        # Format participants with usernames
        formatted_participants = []
        total_g_disbursed = 0

        if participants and participants.data:
            for p in participants.data:
                wallet = p.get('wallet_address', '')
                amount = float(p.get('amount_g$', 0))
                total_g_disbursed += amount

                # Get username
                username = supabase_logger.get_username(wallet)

                formatted_participants.append({
                    'wallet_address': wallet,
                    'display_name': username if username else f"{wallet[:6]}...{wallet[-4:]}",
                    'amount_g$': amount,
                    'amount_formatted': f"{amount:,.1f} G$",
                    'timestamp': p.get('timestamp'),
                    'transaction_hash': p.get('transaction_hash', 'N/A'),
                    'quiz_id': p.get('quiz_id', 'N/A')
                })

        return jsonify({
            "success": True,
            "participants": formatted_participants,
            "total_count": len(formatted_participants),
            "total_g_disbursed": total_g_disbursed,
            "total_g_disbursed_formatted": f"{total_g_disbursed:,.2f} G$",
            "date": target_date if target_date else datetime.utcnow().strftime('%Y-%m-%d')
        })

    except Exception as e:
        logger.error(f"❌ Error getting Learn & Earn participants: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "participants": [],
            "total_count": 0,
            "total_g_disbursed": 0,
            "error": str(e)
        })

@routes.route("/api/screenshot/<path:filename>", methods=["GET"])
def serve_screenshot(filename):
    """Serve screenshot from Object Storage"""
    try:
        from object_storage_client import download_screenshot
        from flask import send_file
        import io

        # Download from Object Storage
        file_data = download_screenshot(filename)

        if not file_data:
            return jsonify({"success": False, "error": "Screenshot not found"}), 404

        # Return as image
        return send_file(
            io.BytesIO(file_data),
            mimetype='image/png',
            as_attachment=False
        )

    except Exception as e:
        logger.error(f"❌ Error serving screenshot: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/community-screenshots", methods=["GET"])
def get_community_screenshots():
    """Get community screenshots for homepage"""
    try:
        from community_stories.community_stories_service import community_stories_service
        from supabase_client import get_supabase_client

        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "screenshots": []})

        limit = int(request.args.get('limit', 12))

        result = community_stories_service.get_screenshots_for_homepage(limit)

        if result.get('success') and result.get('screenshots'):
            # Add usernames
            from supabase_client import supabase_logger
            for screenshot in result['screenshots']:
                wallet = screenshot.get('wallet_address', '')
                username = supabase_logger.get_username(wallet)
                screenshot['display_name'] = username if username else f"{wallet[:6]}...{wallet[-4:]}"

        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Error getting community screenshots: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/recent-community-stories", methods=["GET"])
def get_recent_community_stories():
    """Get recent approved community stories"""
    try:
        from supabase_client import get_supabase_client

        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "stories": []})

        limit = int(request.args.get('limit', 50))

        # Get approved community stories (both high and low rewards)
        stories = safe_supabase_operation(
            lambda: supabase.table('community_stories_submissions')\
                .select('*')\
                .in_('status', ['approved_high', 'approved_low'])\
                .order('reviewed_at', desc=True)\
                .limit(limit)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get recent community stories"
        )

        # Format stories with username
        formatted_stories = []
        if stories and stories.data:
            for story in stories.data:
                wallet = story.get('wallet_address', '')
                username = supabase_logger.get_username(wallet)

                formatted_stories.append({
                    'wallet_address': wallet,
                    'display_name': username if username else f"{wallet[:6]}...{wallet[-4:]}",
                    'reward_amount': float(story.get('reward_amount', 0)),
                    'reviewed_at': story.get('reviewed_at'),
                    'status': story.get('status'),
                    'tweet_url': story.get('tweet_url', ''),
                    'submission_id': story.get('submission_id')
                })

        return jsonify({
            "success": True,
            "stories": formatted_stories,
            "total_count": len(formatted_stories)
        })

    except Exception as e:
        logger.error(f"❌ Error getting recent community stories: {e}")
        return jsonify({"success": False, "stories": []})

@routes.route("/")
def index():
    """Main homepage with Connect Wallet style"""
    # If already logged in, redirect to overview
    if session.get("verified") and session.get("wallet"):
        return redirect("/overview")
    return render_template("homepage.html")

@routes.route("/login")
def login_page():
    """Legacy login page - redirect to homepage"""
    return redirect(url_for("routes.index"))

@routes.route("/login", methods=["POST"])
def login():
    """Legacy login endpoint - redirects to main page"""
    # This legacy login should ideally be updated or removed
    # For now, assuming it sets session['wallet'] and session['verified'] if needed
    # For the purpose of this edit, we assume session['wallet'] is set by other means if this is bypassed
    # If session['wallet'] is not set, the subsequent checks will handle redirection.
    return redirect(url_for("routes.index"))

@routes.route("/verify-ubi-page")
def verify_ubi_page():
    """Legacy verify page - redirects to main page"""
    return redirect(url_for("routes.index"))

@routes.route("/verify-ubi", methods=["POST"])
def verify_ubi():
    try:
        data = request.get_json()
        wallet_address = data.get("wallet", "").strip()
        referral_code = data.get("referral_code", None) # Get referral code from request
        track_analytics = data.get("track_analytics", False)

        if not wallet_address:
            return jsonify({"status": "error", "message": "⚠️ Wallet address required"}), 400

        # Use the correct function name from blockchain.py
        result = has_recent_ubi_claim(wallet_address)

        if result["status"] == "success":
            # Track successful verification
            analytics.track_verification_attempt(wallet_address, True)
            analytics.track_user_session(wallet_address)

            # Store in session
            session["wallet"] = wallet_address
            session["verified"] = True

            # Extract block and amount from the latest activity
            latest_activity = result.get("summary", {}).get("latest_activity", {})
            block_number = latest_activity.get("block", "N/A")
            claim_amount = latest_activity.get("amount", "N/A")

            # Process referral rewards automatically (CRITICAL: This happens during UBI verification)
            referral_recorded = False
            referral_error_message = None
            referrer_reward_tx = None
            referee_reward_tx = None

            if referral_code and referral_code.strip():
                try:
                    from referral_program.referral_service import referral_service
                    from referral_program.blockchain import referral_blockchain_service
                    from datetime import datetime

                    logger.info(f"🎁 ========================================")
                    logger.info(f"🎁 REFERRAL REWARD PROCESSING STARTED")
                    logger.info(f"🎁 Code: {referral_code}")
                    logger.info(f"🎁 New User (Referee): {wallet_address[:8]}...")
                    logger.info(f"🎁 ========================================")

                    # Step 1: Validate referral code
                    validation = referral_service.validate_referral_code(referral_code)
                    logger.info(f"🔍 Step 1 - Validation: {validation}")

                    if not validation.get('valid'):
                        error_msg = validation.get('error', 'Invalid referral code')
                        logger.error(f"❌ FAILED: {error_msg}")
                        raise Exception(error_msg)

                    referrer_wallet = validation['referrer_wallet']
                    logger.info(f"✅ Valid code - Referrer: {referrer_wallet[:8]}...")

                    # Step 2: Record the referral in database
                    logger.info(f"📝 Step 2 - Recording referral in database...")
                    record_result = referral_service.record_referral(
                        referral_code=referral_code,
                        referee_wallet=wallet_address
                    )
                    logger.info(f"🔍 Record result: {record_result}")

                    if not record_result.get('success'):
                        error_msg = record_result.get('error', 'Failed to record referral')
                        logger.error(f"❌ FAILED to record: {error_msg}")
                        raise Exception(error_msg)

                    referral_recorded = True
                    logger.info(f"✅ Referral recorded in database")

                    # Step 3: Disburse 200 G$ to REFERRER (User A who shared the code)
                    logger.info(f"💰 Step 3 - Disbursing 200 G$ to REFERRER {referrer_wallet[:8]}...")
                    referrer_result = referral_blockchain_service.disburse_referral_reward_sync(
                        wallet_address=referrer_wallet,
                        amount=200.0,
                        reward_type='referrer'
                    )
                    logger.info(f"🔍 Referrer disbursement result: {referrer_result}")

                    if referrer_result.get('success'):
                        referrer_reward_tx = referrer_result.get('tx_hash')
                        logger.info(f"✅ Referrer reward sent! TX: {referrer_reward_tx}")
                    else:
                        error_msg = referrer_result.get('error', 'Unknown blockchain error')
                        logger.error(f"❌ Referrer reward FAILED: {error_msg}")
                        referral_error_message = f"Referrer reward failed: {error_msg}"

                    # Step 4: Disburse 100 G$ to REFEREE (New user - User B)
                    logger.info(f"💰 Step 4 - Disbursing 100 G$ to REFEREE (new user) {wallet_address[:8]}...")
                    referee_result = referral_blockchain_service.disburse_referral_reward_sync(
                        wallet_address=wallet_address,
                        amount=100.0,
                        reward_type='referee'
                    )
                    logger.info(f"🔍 Referee disbursement result: {referee_result}")

                    if referee_result.get('success'):
                        referee_reward_tx = referee_result.get('tx_hash')
                        logger.info(f"✅ Referee reward sent! TX: {referee_reward_tx}")
                    else:
                        error_msg = referee_result.get('error', 'Unknown blockchain error')
                        logger.error(f"❌ Referee reward FAILED: {error_msg}")
                        if not referral_error_message:
                            referral_error_message = f"Referee reward failed: {error_msg}"

                    # Step 5: Log rewards to database
                    supabase_client = get_supabase_client()
                    if supabase_client:
                        if referrer_result.get('success'):
                            logger.info(f"📝 Logging referrer reward to database...")
                            safe_supabase_operation(
                                lambda: supabase_client.table('referral_rewards_log').insert({
                                    'wallet_address': referrer_wallet,
                                    'reward_amount': 200.0,
                                    'reward_type': 'referrer',
                                    'referral_code': referral_code,
                                    'tx_hash': referrer_reward_tx,
                                    'created_at': datetime.now().isoformat()
                                }).execute(),
                                fallback_result=None,
                                operation_name="log referrer reward"
                            )

                        if referee_result.get('success'):
                            logger.info(f"📝 Logging referee reward to database...")
                            safe_supabase_operation(
                                lambda: supabase_client.table('referral_rewards_log').insert({
                                    'wallet_address': wallet_address,
                                    'reward_amount': 100.0,
                                    'reward_type': 'referee',
                                    'referral_code': referral_code,
                                    'tx_hash': referee_reward_tx,
                                    'created_at': datetime.now().isoformat()
                                }).execute(),
                                fallback_result=None,
                                operation_name="log referee reward"
                            )

                        # Step 6: Update referral status
                        both_successful = referrer_result.get('success') and referee_result.get('success')
                        status_to_set = 'completed' if both_successful else 'failed'
                        logger.info(f"📝 Updating referral status to: {status_to_set}")

                        safe_supabase_operation(
                            lambda: supabase_client.table('referrals').update({
                                'status': status_to_set,
                                'completed_at': datetime.now().isoformat() if status_to_set == 'completed' else None,
                                'error_message': referral_error_message
                            }).eq('referral_code', referral_code).eq('referee_wallet', wallet_address).execute(),
                            fallback_result=None,
                            operation_name="update referral status"
                        )

                    # Final status log
                    logger.info(f"🎁 ========================================")
                    if referrer_result.get('success') and referee_result.get('success'):
                        logger.info(f"✅ ✅ ✅ REFERRAL REWARDS FULLY SUCCESSFUL! ✅ ✅ ✅")
                        logger.info(f"💰 Referrer {referrer_wallet[:8]}... received 200 G$")
                        logger.info(f"📜 TX: {referrer_reward_tx}")
                        logger.info(f"💰 Referee {wallet_address[:8]}... received 100 G$")
                        logger.info(f"📜 TX: {referee_reward_tx}")
                    else:
                        logger.error(f"⚠️ REFERRAL REWARDS PARTIALLY FAILED")
                        if referrer_result.get('success'):
                            logger.info(f"✅ Referrer got reward: {referrer_reward_tx}")
                        else:
                            logger.error(f"❌ Referrer reward failed")
                        if referee_result.get('success'):
                            logger.info(f"✅ Referee got reward: {referee_reward_tx}")
                        else:
                            logger.error(f"❌ Referee reward failed")
                    logger.info(f"🎁 ========================================")

                except Exception as ref_error:
                    logger.error(f"❌ ❌ ❌ REFERRAL PROCESSING EXCEPTION ❌ ❌ ❌")
                    logger.error(f"❌ Error: {ref_error}")
                    logger.exception("Full referral error traceback:")
                    referral_recorded = False
                    referral_error_message = str(ref_error)
                    logger.error(f"🎁 ========================================")

            # Auto-accept terms for all users - skip terms page
            session['terms_accepted'] = True
            session.permanent = True

            # Check if username is set, redirect to setup if not
            username = supabase_logger.get_username(wallet_address)
            redirect_url = "/setup-username" if not username else "/overview"

            return jsonify({
                "status": "success",
                "message": result["message"],
                "wallet": wallet_address,
                "block_number": block_number,
                "claim_amount": claim_amount,
                "activities": result.get("activities", []),
                "summary": result.get("summary", {}),
                "redirect_to": redirect_url
            })
        else:
            # Track failed verification
            analytics.track_verification_attempt(wallet_address, False)

            # Use the detailed message from blockchain.py
            error_message = result.get("message", "You need to claim G$ in goodwallet.xyz or gooddapp.org once every 48 hours to access GoodMarket.")

            return jsonify({
                "status": "error",
                "message": error_message,
                "reason": "no_recent_claim",
                "help_links": {
                    "goodwallet": "https://goodwallet.xyz",
                    "gooddapp": "https://gooddapp.org"
                }
            }), 400

    except Exception as e:
        logger.exception("Verification error occurred")
        # Return custom message instead of generic error
        error_message = "You need to claim G$ in goodwallet.xyz or gooddapp.org once every 24 hours to access GoodMarket."
        return jsonify({
            "status": "error",
            "message": error_message,
            "reason": "verification_error"
        }), 500

@routes.route("/overview")
def overview():
    wallet = session.get('wallet') or session.get('wallet_address')
    verified = session.get('verified') or session.get('ubi_verified')
    username = None

    # Check if user has valid session
    if wallet and verified:
        # Validate UBI claim is still recent for authenticated users
        from blockchain import has_recent_ubi_claim
        ubi_check = has_recent_ubi_claim(wallet)

        if ubi_check["status"] != "success":
            # UBI claim expired - clear session and show guest view
            logger.warning(f"⚠️ Session expired for {wallet[:8]}... - showing guest view")
            session.clear()
            wallet = None
            verified = False
        else:
            # Valid session - check username
            try:
                username = supabase_logger.get_username(wallet)
                logger.info(f"🔍 Overview username check for {wallet[:8]}...: username={username}")

                # Check if username exists AND is not empty/null
                if username and username.strip():
                    # Valid username exists
                    session['username'] = username
                    session.permanent = True
                else:
                    # No username or empty username - redirect to setup
                    logger.info(f"⚠️ No valid username for {wallet[:8]}..., redirecting to setup")
                    return redirect(url_for("routes.setup_username"))

                # Track overview visit for authenticated users
                analytics.track_page_view(wallet, "overview")
            except Exception as e:
                logger.error(f"❌ Error getting username in overview: {e}")
                import traceback
                logger.error(f"🔍 Traceback: {traceback.format_exc()}")

    # Get analytics - pass None for guest users, wallet for authenticated users
    stats = analytics.get_dashboard_stats(wallet if wallet and verified else None)

    # Debug logging
    logger.info(f"🔍 Overview page - Wallet: {wallet[:8] if wallet else 'Guest'}...")
    logger.info(f"🔍 Overview page - stats keys: {list(stats.keys())}")
    logger.info(f"🔍 Overview page - disbursement_analytics present: {'disbursement_analytics' in stats}")
    if 'disbursement_analytics' in stats:
        logger.info(f"🔍 Overview page - disbursement_analytics keys: {list(stats['disbursement_analytics'].keys())}")
        logger.info(f"🔍 Overview page - breakdown_formatted present: {'breakdown_formatted' in stats['disbursement_analytics']}")

    return render_template("overview.html",
                         wallet=wallet if wallet and verified else None,
                         username=username if username else "Guest",
                         data=stats)

@routes.route("/dashboard")
def dashboard():
    """Dashboard page"""
    wallet = session.get('wallet') or session.get('wallet_address')
    verified = session.get('verified') or session.get('ubi_verified')

    if not wallet or not verified:
        return redirect(url_for("routes.index"))

    # Validate UBI claim is still recent
    from blockchain import has_recent_ubi_claim
    ubi_check = has_recent_ubi_claim(wallet)

    if ubi_check["status"] != "success":
        # UBI claim expired - auto logout and redirect to homepage
        logger.warning(f"⚠️ Auto-logout: UBI verification expired for {wallet[:8]}...")
        session.clear()
        return redirect(url_for("routes.index"))

    # ALWAYS check database for username (source of truth)
    try:
        username = supabase_logger.get_username(wallet)
        logger.info(f"🔍 Dashboard username check for {wallet[:8]}...: {username}")

        # Check if username exists AND is not empty/null
        if username and username.strip():
            # Valid username exists
            session['username'] = username
            session.permanent = True
        else:
            # No username or empty username - redirect to setup
            logger.info(f"⚠️ No valid username for {wallet[:8]}..., redirecting to setup")
            return redirect(url_for("routes.setup_username"))
    except Exception as e:
        logger.error(f"❌ Error getting username from DB: {e}")
        return redirect(url_for("routes.setup_username"))

    # Track dashboard visit
    analytics.track_page_view(wallet, "dashboard")

    # Get user analytics
    stats = analytics.get_dashboard_stats(wallet)

    return render_template("dashboard.html",
                         wallet=wallet,
                         username=username,
                         user_stats=stats.get("user_stats", {}),
                         gooddollar_info=stats.get("gooddollar_info", {}),
                         platform_stats=stats.get("platform_stats", {}))

@routes.route("/track-analytics", methods=["POST"])
def track_analytics_endpoint(): # Renamed to avoid conflict with analytics_service
    try:
        data = request.get_json()
        if not data:
            logger.error("❌ track-analytics: No JSON data received")
            return jsonify({"status": "error", "message": "No data provided"}), 400

        event = data.get("event")
        wallet = data.get("wallet")
        # Add username to track if available in request data
        username = data.get("username")

        logger.info(f"🔍 track-analytics: event='{event}', wallet='{wallet}', username='{username}'")

        if event and wallet:
            # Track page view (analytics.track_page_view only takes wallet and page)
            analytics.track_page_view(wallet, event)
            return jsonify({"status": "success"})

        missing = []
        if not event:
            missing.append("event")
        if not wallet:
            missing.append("wallet")

        error_msg = f"Missing required fields: {', '.join(missing)}"
        logger.error(f"❌ track-analytics: {error_msg}")
        return jsonify({"status": "error", "message": error_msg}), 400

    except Exception as e:
        logger.exception("❌ track-analytics error") # Use logger.exception for full traceback
        return jsonify({"status": "error", "message": str(e)}), 500

@routes.route("/ubi-tracker")
def ubi_tracker_page():
    if not session.get("verified") or not session.get("wallet"):
        return redirect(url_for("routes.index"))

    wallet = session.get("wallet")
    # Check if user has set username, redirect to setup if not
    username = supabase_logger.get_username(wallet)
    if not username:
        return redirect(url_for("routes.setup_username"))

    analytics.track_page_view(wallet, "ubi_tracker")

    return render_template("ubi_tracker.html",
                         wallet=wallet,
                         username=username, # Pass username to template
                         contract_count=len(GOODDOLLAR_CONTRACTS))

@routes.route("/logout")
def logout():
    wallet = session.get("wallet")
    if wallet:
        # Log logout to Supabase
        supabase_logger.log_logout(wallet)

    # Completely clear the session
    session.clear()

    # Create response with redirect
    response = redirect(url_for("routes.index"))

    # Clear all session cookies
    response.set_cookie('session', '', expires=0, path='/')
    response.set_cookie('wallet', '', expires=0, path='/')
    response.set_cookie('verified', '', expires=0, path='/')
    response.set_cookie('username', '', expires=0, path='/')

    # Add cache control headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response


@routes.route("/news")
def news_feed_page():
    if not session.get("verified") or not session.get("wallet"):
        return redirect(url_for("routes.index"))

    wallet = session.get("wallet")
    # Check if user has set username, redirect to setup if not
    username = supabase_logger.get_username(wallet)
    if not username:
        return redirect(url_for("routes.setup_username"))

    # Track news page visit
    analytics.track_page_view(wallet, "news_feed")

    # Get news feed data for initial page load
    from news_feed import news_feed_service

    featured_news = news_feed_service.get_featured_news(limit=3)
    recent_news = news_feed_service.get_news_feed(limit=10)
    news_stats = news_feed_service.get_news_stats()

    return render_template("news_feed.html",
                         wallet=wallet,
                         username=username, # Pass username to template
                         featured_news=featured_news,
                         recent_news=recent_news,
                         news_stats=news_stats,
                         categories=news_feed_service.categories)

@routes.route("/api/admin/check", methods=["GET"])
@auth_required
def check_admin_status():
    """Check if current user is admin"""
    try:
        wallet = session.get("wallet")
        from supabase_client import is_admin

        is_admin_user = is_admin(wallet)

        return jsonify({
            "success": True,
            "is_admin": is_admin_user,
            "wallet": wallet[:8] + "..." if wallet else None
        })
    except Exception as e:
        logger.error(f"❌ Admin check error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/users", methods=["GET"])
@admin_required
def get_all_users():
    """Get all users (admin only)"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        # Get users with pagination
        users = safe_supabase_operation(
            lambda: supabase.table('user_data')\
                .select('wallet_address, username, ubi_verified, total_logins, last_login, created_at')\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get all users"
        )

        return jsonify({
            "success": True,
            "users": users.data if users.data else [],
            "count": len(users.data) if users.data else 0
        })
    except Exception as e:
        logger.error(f"❌ Get users error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/stats", methods=["GET"])
@admin_required
def get_admin_stats():
    """Get platform statistics (admin only)"""
    try:
        from analytics_service import analytics

        # Get comprehensive platform stats using the correct method
        platform_stats = analytics.get_global_analytics()

        # Extract relevant stats for admin dashboard
        stats = {
            "total_users": platform_stats.get("metrics", {}).get("total_users", 0),
            "verified_users": platform_stats.get("metrics", {}).get("successful_verifications", 0),
            "total_page_views": platform_stats.get("user_activity", {}).get("total_page_views", 0),
            "verification_rate": platform_stats.get("verification_stats", {}).get("success_rate", "0%")
        }

        return jsonify({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"❌ Get admin stats error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/set-admin", methods=["POST"])
@admin_required
def set_user_admin_status():
    """Set admin status for a user (admin only)"""
    try:
        from supabase_client import set_admin_status, log_admin_action

        data = request.json
        target_wallet = data.get("wallet_address")
        is_admin_status = data.get("is_admin", False)

        if not target_wallet:
            return jsonify({"success": False, "error": "Wallet address required"}), 400

        admin_wallet = session.get("wallet")

        # Set admin status
        result = set_admin_status(target_wallet, is_admin_status)

        if result.get("success"):
            # Log admin action
            log_admin_action(
                admin_wallet=admin_wallet,
                action_type="set_admin_status",
                target_wallet=target_wallet,
                action_details={"is_admin": is_admin_status}
            )

        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Set admin status error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/actions-log", methods=["GET"])
@admin_required
def get_admin_actions_log():
    """Get admin actions log (admin only)"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        # Get admin actions with pagination
        actions = safe_supabase_operation(
            lambda: supabase.table('admin_actions_log')\
                .select('*')\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get admin actions log"
        )

        return jsonify({
            "success": True,
            "actions": actions.data if actions.data else [],
            "count": len(actions.data) if actions.data else 0
        })
    except Exception as e:
        logger.error(f"❌ Get admin actions log error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/quiz-questions", methods=["GET"])
@admin_required
def get_quiz_questions():
    """Get all quiz questions (admin only)"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        logger.info("📚 Fetching quiz questions from Supabase 'quiz_questions' table...")

        # Get all quiz questions
        questions = safe_supabase_operation(
            lambda: supabase.table('quiz_questions')\
                .select('*')\
                .order('created_at', desc=True)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get quiz questions"
        )

        logger.info(f"✅ Retrieved {len(questions.data) if questions.data else 0} questions from Supabase")
        if questions.data and len(questions.data) > 0:
            logger.info(f"📝 Sample question: ID={questions.data[0].get('question_id')}, Question={questions.data[0].get('question')[:50]}...")

        return jsonify({
            "success": True,
            "questions": questions.data if questions.data else [],
            "count": len(questions.data) if questions.data else 0,
            "data_source": "supabase_quiz_questions_table"
        })
    except Exception as e:
        logger.error(f"❌ Get quiz questions error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/quiz-questions", methods=["POST"])
@admin_required
def add_quiz_question():
    """Add new quiz question (admin only)"""
    try:
        data = request.json

        # Validate required fields
        required_fields = ['question_id', 'question', 'answer_a', 'answer_b', 'answer_c', 'answer_d', 'correct']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        # Validate correct answer is A, B, C, or D
        if data['correct'].upper() not in ['A', 'B', 'C', 'D']:
            return jsonify({"success": False, "error": "Correct answer must be A, B, C, or D"}), 400

        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Check if question_id already exists
        existing = safe_supabase_operation(
            lambda: supabase.table('quiz_questions')\
                .select('question_id')\
                .eq('question_id', data['question_id'])\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="check question_id"
        )

        if existing.data and len(existing.data) > 0:
            return jsonify({"success": False, "error": "Question ID already exists"}), 400

        # Add new question
        from datetime import datetime
        question_data = {
            'question_id': data['question_id'],
            'question': data['question'],
            'answer_a': data['answer_a'],
            'answer_b': data['answer_b'],
            'answer_c': data['answer_c'],
            'answer_d': data['answer_d'],
            'correct': data['correct'].upper(),
            'created_at': datetime.utcnow().isoformat() + 'Z'
        }

        result = safe_supabase_operation(
            lambda: supabase.table('quiz_questions').insert(question_data).execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="add quiz question"
        )

        if result.data:
            # Log admin action
            admin_wallet = session.get("wallet")
            log_admin_action(
                admin_wallet=admin_wallet,
                action_type="add_quiz_question",
                action_details={"question_id": data['question_id']}
            )

            logger.info(f"✅ Quiz question added: {data['question_id']}")
            return jsonify({"success": True, "question": result.data[0]})
        else:
            return jsonify({"success": False, "error": "Failed to add question"}), 500

    except Exception as e:
        logger.error(f"❌ Add quiz question error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/quiz-questions/<question_id>", methods=["PUT"])
@admin_required
def update_quiz_question(question_id):
    """Update quiz question (admin only)"""
    try:
        data = request.json

        # Validate correct answer if provided
        if 'correct' in data and data['correct'].upper() not in ['A', 'B', 'C', 'D']:
            return jsonify({"success": False, "error": "Correct answer must be A, B, C, or D"}), 400

        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Build update data
        update_data = {}
        allowed_fields = ['question', 'answer_a', 'answer_b', 'answer_c', 'answer_d', 'correct']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field].upper() if field == 'correct' else data[field]

        if not update_data:
            return jsonify({"success": False, "error": "No valid fields to update"}), 400

        # Update question
        result = safe_supabase_operation(
            lambda: supabase.table('quiz_questions')\
                .update(update_data)\
                .eq('question_id', question_id)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="update quiz question"
        )

        if result.data:
            # Log admin action
            admin_wallet = session.get("wallet")
            log_admin_action(
                admin_wallet=admin_wallet,
                action_type="update_quiz_question",
                action_details={"question_id": question_id, "updated_fields": list(update_data.keys())}
            )

            logger.info(f"✅ Quiz question updated: {question_id}")
            return jsonify({"success": True, "question": result.data[0]})
        else:
            return jsonify({"success": False, "error": "Question not found"}), 404

    except Exception as e:
        logger.error(f"❌ Update quiz question error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/quiz-questions/<question_id>", methods=["DELETE"])
@admin_required
def delete_quiz_question(question_id):
    """Delete quiz question (admin only)"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Delete question
        result = safe_supabase_operation(
            lambda: supabase.table('quiz_questions')\
                .delete()\
                .eq('question_id', question_id)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="delete quiz question"
        )

        if result.data:
            # Log admin action
            admin_wallet = session.get("wallet")
            log_admin_action(
                admin_wallet=admin_wallet,
                action_type="delete_quiz_question",
                action_details={"question_id": question_id}
            )

            logger.info(f"✅ Quiz question deleted: {question_id}")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Question not found"}), 404

    except Exception as e:
        logger.error(f"❌ Delete quiz question error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/quiz-questions/delete-all", methods=["DELETE"])
@admin_required
def delete_all_quiz_questions():
    """Delete all quiz questions (admin only)"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Get count of questions before deletion
        count_result = safe_supabase_operation(
            lambda: supabase.table('quiz_questions').select('quiz_id').execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="count quiz questions"
        )

        question_count = len(count_result.data) if count_result.data else 0

        if question_count == 0:
            return jsonify({"success": False, "error": "No questions to delete"}), 400

        # Delete all questions
        result = safe_supabase_operation(
            lambda: supabase.table('quiz_questions').delete().neq('quiz_id', 0).execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="delete all quiz questions"
        )

        # Log admin action
        admin_wallet = session.get("wallet")
        log_admin_action(
            admin_wallet=admin_wallet,
            action_type="delete_all_quiz_questions",
            action_details={"deleted_count": question_count}
        )

        logger.info(f"✅ All quiz questions deleted: {question_count} questions")
        return jsonify({
            "success": True,
            "deleted_count": question_count
        })

    except Exception as e:
        logger.error(f"❌ Delete all quiz questions error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/broadcast-message", methods=["POST"])
@admin_required
def send_broadcast_message():
    """Send broadcast message to all users (admin only)"""
    try:
        data = request.json
        title = data.get('title', '').strip()
        message = data.get('message', '').strip()

        if not title or not message:
            return jsonify({"success": False, "error": "Title and message are required"}), 400

        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        admin_wallet = session.get("wallet")

        from datetime import datetime
        broadcast_data = {
            'title': title,
            'message': message,
            'sender_wallet': admin_wallet,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }

        result = safe_supabase_operation(
            lambda: supabase.table('admin_broadcast_messages').insert(broadcast_data).execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="send broadcast message"
        )

        if result.data:
            # Log admin action
            log_admin_action(
                admin_wallet=admin_wallet,
                action_type="send_broadcast_message",
                action_details={"title": title, "message_length": len(message)}
            )

            logger.info(f"✅ Broadcast message sent by admin {admin_wallet[:8]}...")
            return jsonify({
                "success": True,
                "message": "Broadcast message sent successfully!",
                "broadcast_id": result.data[0].get('id')
            })
        else:
            return jsonify({"success": False, "error": "Failed to send broadcast message"}), 500

    except Exception as e:
        logger.error(f"❌ Send broadcast message error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/broadcast-messages", methods=["GET"])
@admin_required
def get_broadcast_messages():
    """Get all broadcast messages (admin only)"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        limit = int(request.args.get('limit', 50))

        messages = safe_supabase_operation(
            lambda: supabase.table('admin_broadcast_messages')\
                .select('*')\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get broadcast messages"
        )

        return jsonify({
            "success": True,
            "messages": messages.data if messages.data else [],
            "count": len(messages.data) if messages.data else 0
        })

    except Exception as e:
        logger.error(f"❌ Get broadcast messages error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/broadcast-message/<int:broadcast_id>", methods=["DELETE"])
@admin_required
def delete_broadcast_message(broadcast_id):
    """Delete/deactivate broadcast message (admin only)"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Deactivate instead of delete
        result = safe_supabase_operation(
            lambda: supabase.table('admin_broadcast_messages')\
                .update({'is_active': False})\
                .eq('id', broadcast_id)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="deactivate broadcast message"
        )

        if result.data:
            admin_wallet = session.get("wallet")
            log_admin_action(
                admin_wallet=admin_wallet,
                action_type="delete_broadcast_message",
                action_details={"broadcast_id": broadcast_id}
            )

            logger.info(f"✅ Broadcast message {broadcast_id} deactivated")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Message not found"}), 404

    except Exception as e:
        logger.error(f"❌ Delete broadcast message error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/publish-news", methods=["POST"])
@admin_required
def publish_news_article():
    """Publish a news article (admin only)"""
    try:
        from news_feed import news_feed_service
        
        # Get form data
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'announcement')
        priority = request.form.get('priority', 'medium')
        featured = request.form.get('featured') == 'true'
        url = request.form.get('url', '').strip()
        
        # Validate required fields
        if not title or not content:
            return jsonify({"success": False, "error": "Title and content are required"}), 400
        
        # Handle image upload if present
        image_url = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename:
                # Upload to ImgBB
                try:
                    import requests
                    import base64
                    
                    imgbb_api_key = os.getenv('IMGBB_API_KEY')
                    if not imgbb_api_key:
                        logger.warning("⚠️ IMGBB_API_KEY not configured - skipping image upload")
                    else:
                        # Reset file pointer to beginning and read image
                        image_file.seek(0)
                        image_data = image_file.read()
                        
                        # Validate image data
                        if not image_data or len(image_data) == 0:
                            logger.error("❌ Image file is empty")
                            return jsonify({"success": False, "error": "Image file is empty"}), 400
                        
                        # Encode to base64
                        encoded_image = base64.b64encode(image_data).decode('utf-8')
                        
                        logger.info(f"📤 Uploading image to ImgBB: {image_file.filename} ({len(image_data)} bytes)")
                        
                        # Upload to ImgBB
                        imgbb_response = requests.post(
                            'https://api.imgbb.com/1/upload',
                            data={
                                'key': imgbb_api_key,
                                'image': encoded_image,
                                'name': f"news_{title[:30]}"
                            },
                            timeout=30
                        )
                        
                        logger.info(f"📥 ImgBB Response: {imgbb_response.status_code}")
                        
                        if imgbb_response.status_code == 200:
                            imgbb_data = imgbb_response.json()
                            if imgbb_data.get('success'):
                                image_url = imgbb_data['data']['url']
                                logger.info(f"✅ Image uploaded to ImgBB: {image_url}")
                            else:
                                error_msg = imgbb_data.get('error', {}).get('message', 'Unknown error')
                                logger.error(f"❌ ImgBB API error: {error_msg}")
                                return jsonify({"success": False, "error": f"Image upload failed: {error_msg}"}), 500
                        else:
                            logger.error(f"❌ ImgBB upload failed: {imgbb_response.status_code} - {imgbb_response.text[:500]}")
                            return jsonify({"success": False, "error": f"Image upload failed with status {imgbb_response.status_code}"}), 500
                            
                except Exception as img_error:
                    logger.error(f"❌ Image upload error: {img_error}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    return jsonify({"success": False, "error": f"Image upload error: {str(img_error)}"}), 500
        
        # Get admin wallet
        admin_wallet = session.get("wallet")
        
        # Add news article
        result = news_feed_service.add_news_article(
            title=title,
            content=content,
            category=category,
            priority=priority,
            author=f"Admin ({admin_wallet[:8]}...)",
            featured=featured,
            image_url=image_url,
            url=url if url else None
        )
        
        if result.get('success'):
            # Log admin action
            log_admin_action(
                admin_wallet=admin_wallet,
                action_type="publish_news_article",
                action_details={
                    "title": title,
                    "category": category,
                    "featured": featured,
                    "has_image": bool(image_url)
                }
            )
            
            logger.info(f"✅ News article published: {title}")
            return jsonify({
                "success": True,
                "message": "News article published successfully!",
                "article": result.get('article')
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Failed to publish article')
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Publish news article error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/maintenance/learn-earn", methods=["GET"])
@admin_required
def get_learn_earn_maintenance():
    """Get Learn & Earn maintenance status"""
    try:
        from maintenance_service import maintenance_service

        status = maintenance_service.get_maintenance_status('learn_earn')
        return jsonify(status)
    except Exception as e:
        logger.error(f"❌ Error getting maintenance status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/maintenance/learn-earn", methods=["POST"])
@admin_required
def set_learn_earn_maintenance():
    """Set Learn & Earn maintenance status"""
    try:
        from maintenance_service import maintenance_service

        data = request.json
        is_maintenance = data.get('is_maintenance', False)
        message = data.get('message', '')
        admin_wallet = session.get('wallet')

        if is_maintenance and not message:
            return jsonify({
                "success": False,
                "error": "Custom message is required when enabling maintenance mode"
            }), 400

        result = maintenance_service.set_maintenance_status(
            'learn_earn',
            is_maintenance,
            message,
            admin_wallet
        )

        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Error setting maintenance status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/quiz-settings", methods=["GET"])
@admin_required
def get_quiz_settings():
    """Get current quiz settings"""
    try:
        from learn_and_earn.learn_and_earn import quiz_manager

        settings = quiz_manager.get_quiz_settings()
        return jsonify({
            "success": True,
            "settings": settings
        })
    except Exception as e:
        logger.error(f"❌ Error getting quiz settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/community-stories-settings", methods=["GET"])
@admin_required
def get_community_stories_settings():
    """Get Community Stories settings (admin only)"""
    try:
        from community_stories.community_stories_service import community_stories_service

        config = community_stories_service.get_config()

        # Get message from database
        supabase = get_supabase_client()
        message = None

        if supabase:
            result = safe_supabase_operation(
                lambda: supabase.table('maintenance_settings')\
                    .select('custom_message')\
                    .eq('feature_name', 'community_stories_message')\
                    .execute(),
                fallback_result=type('obj', (object,), {'data': []})(),
                operation_name="get community stories message"
            )

            if result.data and len(result.data) > 0:
                message = result.data[0].get('custom_message')

        return jsonify({
            "success": True,
            "settings": {
                "low_reward": config['LOW_REWARD'],
                "high_reward": config['HIGH_REWARD'],
                "required_mentions": config['REQUIRED_MENTIONS'],
                "window_start_day": config['WINDOW_START_DAY'],
                "window_end_day": config['WINDOW_END_DAY'],
                "message": message or """💰 Earn G$ by sharing our story:
2,000 G$ - Text post on Twitter/X
5,000 G$ - Video post (min. 30 seconds)

📋 Requirements:
Must use hashtags: @gooddollarorg @GoodDollarTeam
Post must be public
Original content only

📅 Participation Schedule:
Opens: 26th of each month at 12:00 AM UTC
Closes: 30th of each month at 11:59 PM UTC
Duration: 5 days only each month
After reward: Blocked until next 26th

⚠️ Late submissions after 30th are NOT accepted!"""
            }
        })
    except Exception as e:
        logger.error(f"❌ Error getting Community Stories settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/community-stories-settings", methods=["POST"])
@admin_required
def update_community_stories_settings():
    """Update Community Stories settings (admin only)"""
    try:
        data = request.json
        low_reward = data.get('low_reward')
        high_reward = data.get('high_reward')
        required_mentions = data.get('required_mentions')
        window_start_day = data.get('window_start_day')
        window_end_day = data.get('window_end_day')
        message = data.get('message', '').strip()

        if not all([low_reward, high_reward, required_mentions, window_start_day, window_end_day]):
            return jsonify({"success": False, "error": "All fields are required"}), 400

        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Store settings in database using custom_message field for JSON data
        settings_json = json.dumps({
            'low_reward': float(low_reward),
            'high_reward': float(high_reward),
            'required_mentions': str(required_mentions),
            'window_start_day': int(window_start_day),
            'window_end_day': int(window_end_day)
        })

        settings_data = {
            'feature_name': 'community_stories_config',
            'is_maintenance': False,  # Use boolean field properly
            'custom_message': settings_json  # Store JSON in text field
        }

        # Check if exists
        existing = safe_supabase_operation(
            lambda: supabase.table('maintenance_settings')\
                .select('id')\
                .eq('feature_name', 'community_stories_config')\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="check community stories config"
        )

        if existing.data and len(existing.data) > 0:
            result = safe_supabase_operation(
                lambda: supabase.table('maintenance_settings')\
                    .update(settings_data)\
                    .eq('feature_name', 'community_stories_config')\
                    .execute(),
                fallback_result=type('obj', (object,), {'data': []})(),
                operation_name="update community stories config"
            )
        else:
            result = safe_supabase_operation(
                lambda: supabase.table('maintenance_settings').insert(settings_data).execute(),
                fallback_result=type('obj', (object,), {'data': []})(),
                operation_name="insert community stories config"
            )

        # Store message separately
        if message:
            message_data = {
                'feature_name': 'community_stories_message',
                'is_maintenance': False,  # Use boolean field properly
                'custom_message': message  # Store message in text field
            }

            existing_msg = safe_supabase_operation(
                lambda: supabase.table('maintenance_settings')\
                    .select('id')\
                    .eq('feature_name', 'community_stories_message')\
                    .execute(),
                fallback_result=type('obj', (object,), {'data': []})(),
                operation_name="check community stories message"
            )

            if existing_msg.data and len(existing_msg.data) > 0:
                safe_supabase_operation(
                    lambda: supabase.table('maintenance_settings')\
                        .update(message_data)\
                        .eq('feature_name', 'community_stories_message')\
                        .execute(),
                    fallback_result=type('obj', (object,), {'data': []})(),
                    operation_name="update community stories message"
                )
            else:
                safe_supabase_operation(
                    lambda: supabase.table('maintenance_settings').insert(message_data).execute(),
                    fallback_result=type('obj', (object,), {'data': []})(),
                    operation_name="insert community stories message"
                )

        if result.data:
            # Log admin action
            admin_wallet = session.get('wallet')
            log_admin_action(
                admin_wallet=admin_wallet,
                action_type="update_community_stories_settings",
                action_details={
                    "low_reward": low_reward,
                    "high_reward": high_reward,
                    "window_start_day": window_start_day,
                    "window_end_day": window_end_day,
                    "message_updated": bool(message)
                }
            )

            logger.info(f"✅ Community Stories settings updated by admin {admin_wallet[:8]}...")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to update settings"}), 500

    except Exception as e:
        logger.error(f"❌ Error updating Community Stories settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/insufficient-balance-message", methods=["GET"])
@admin_required
def get_insufficient_balance_message():
    """Get current insufficient balance error message"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Get message from maintenance_settings table
        result = safe_supabase_operation(
            lambda: supabase.table('maintenance_settings')\
                .select('custom_message')\
                .eq('feature_name', 'learn_earn_insufficient_balance')\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get insufficient balance message"
        )

        message = None
        if result.data and len(result.data) > 0:
            message = result.data[0].get('custom_message')

        return jsonify({
            "success": True,
            "message": message
        })
    except Exception as e:
        logger.error(f"❌ Error getting insufficient balance message: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/insufficient-balance-message", methods=["POST"])
@admin_required
def update_insufficient_balance_message():
    """Update insufficient balance error message"""
    try:
        data = request.json
        message = data.get('message', '').strip()

        if not message:
            return jsonify({
                "success": False,
                "error": "Message is required"
            }), 400

        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Check if record exists
        existing = safe_supabase_operation(
            lambda: supabase.table('maintenance_settings')\
                .select('id')\
                .eq('feature_name', 'learn_earn_insufficient_balance')\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="check existing message"
        )

        if existing.data and len(existing.data) > 0:
            # Update existing record
            result = safe_supabase_operation(
                lambda: supabase.table('maintenance_settings')\
                    .update({'custom_message': message})\
                    .eq('feature_name', 'learn_earn_insufficient_balance')\
                    .execute(),
                fallback_result=type('obj', (object,), {'data': []})(),
                operation_name="update insufficient balance message"
            )
        else:
            # Insert new record
            from datetime import datetime
            result = safe_supabase_operation(
                lambda: supabase.table('maintenance_settings').insert({
                    'feature_name': 'learn_earn_insufficient_balance',
                    'is_maintenance': False,
                    'custom_message': message,
                    'created_at': datetime.utcnow().isoformat()
                }).execute(),
                fallback_result=type('obj', (object,), {'data': []})(),
                operation_name="insert insufficient balance message"
            )

        if result.data:
            # Log admin action
            admin_wallet = session.get('wallet')
            log_admin_action(
                admin_wallet=admin_wallet,
                action_type="update_insufficient_balance_message",
                action_details={"message_length": len(message)}
            )

            logger.info(f"✅ Insufficient balance message updated by admin {admin_wallet[:8]}...")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to update message"}), 500

    except Exception as e:
        logger.error(f"❌ Error updating insufficient balance message: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/quiz-settings", methods=["POST"])
@admin_required
def update_quiz_settings():
    """Update quiz settings"""
    try:
        from learn_and_earn.learn_and_earn import quiz_manager

        data = request.json
        questions_per_quiz = data.get('questions_per_quiz')
        time_per_question = data.get('time_per_question')
        max_reward_per_quiz = data.get('max_reward_per_quiz')

        # Validate inputs
        if questions_per_quiz is not None and (questions_per_quiz < 5 or questions_per_quiz > 30):
            return jsonify({
                "success": False,
                "error": "Questions per quiz must be between 5 and 30"
            }), 400

        if time_per_question is not None and (time_per_question < 10 or time_per_question > 60):
            return jsonify({
                "success": False,
                "error": "Time per question must be between 10 and 60 seconds"
            }), 400

        if max_reward_per_quiz is not None and (max_reward_per_quiz < 500 or max_reward_per_quiz > 10000):
            return jsonify({
                "success": False,
                "error": "Max reward must be between 500 and 10,000 G$"
            }), 400

        result = quiz_manager.update_quiz_settings(
            questions_per_quiz=questions_per_quiz,
            time_per_question=time_per_question,
            max_reward_per_quiz=max_reward_per_quiz
        )

        if result.get('success'):
            # Log admin action
            admin_wallet = session.get('wallet')
            log_admin_action(
                admin_wallet=admin_wallet,
                action_type="update_quiz_settings",
                action_details={
                    "questions_per_quiz": questions_per_quiz,
                    "time_per_question": time_per_question,
                    "max_reward_per_quiz": max_reward_per_quiz
                }
            )

        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Error updating quiz settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/referral/check/<referral_code>", methods=["GET"])
def check_referral_status(referral_code):
    """Check referral code status and history (for debugging)"""
    try:
        from referral_program.referral_service import referral_service

        # Validate code
        validation = referral_service.validate_referral_code(referral_code)

        # Get referrals using this code
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        referrals = safe_supabase_operation(
            lambda: supabase.table('referrals').select('*').eq('referral_code', referral_code).execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get referrals by code"
        )

        rewards = safe_supabase_operation(
            lambda: supabase.table('referral_rewards_log').select('*').eq('referral_code', referral_code).execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get rewards by code"
        )

        return jsonify({
            "success": True,
            "referral_code": referral_code,
            "validation": validation,
            "referrals": referrals.data if referrals.data else [],
            "rewards": rewards.data if rewards.data else [],
            "total_referrals": len(referrals.data) if referrals.data else 0,
            "total_rewards": len(rewards.data) if rewards.data else 0
        })
    except Exception as e:
        logger.error(f"❌ Error checking referral status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/daily-tasks/pending", methods=["GET"])
@admin_required
def get_pending_daily_tasks():
    """Get pending daily task submissions (admin only)"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Get pending Telegram tasks
        telegram_pending = safe_supabase_operation(
            lambda: supabase.table('telegram_task_log')\
                .select('*')\
                .eq('status', 'pending')\
                .order('created_at', desc=False)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get pending telegram tasks"
        )

        # Get pending Twitter tasks
        twitter_pending = safe_supabase_operation(
            lambda: supabase.table('twitter_task_log')\
                .select('*')\
                .eq('status', 'pending')\
                .order('created_at', desc=False)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get pending twitter tasks"
        )

        telegram_tasks = []
        if telegram_pending.data:
            for task in telegram_pending.data:
                telegram_tasks.append({
                    'id': task.get('id'),
                    'wallet_address': task.get('wallet_address'),
                    'url': task.get('telegram_url'),
                    'reward_amount': task.get('reward_amount'),
                    'created_at': task.get('created_at'),
                    'platform': 'telegram'
                })

        twitter_tasks = []
        if twitter_pending.data:
            for task in twitter_pending.data:
                twitter_tasks.append({
                    'id': task.get('id'),
                    'wallet_address': task.get('wallet_address'),
                    'url': task.get('twitter_url'),
                    'reward_amount': task.get('reward_amount'),
                    'created_at': task.get('created_at'),
                    'platform': 'twitter'
                })

        return jsonify({
            "success": True,
            "telegram_tasks": telegram_tasks,
            "twitter_tasks": twitter_tasks,
            "total_pending": len(telegram_tasks) + len(twitter_tasks)
        })

    except Exception as e:
        logger.error(f"❌ Error getting pending tasks: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/daily-tasks/approve", methods=["POST"])
@admin_required
def approve_daily_task():
    """Approve a daily task submission (admin only)"""
    try:
        data = request.json
        submission_id = data.get('submission_id')
        platform = data.get('platform')  # 'telegram' or 'twitter'
        admin_wallet = session.get('wallet')

        if not submission_id or not platform:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            if platform == 'telegram':
                from telegram_task.telegram_task import telegram_task_service
                result = loop.run_until_complete(
                    telegram_task_service.approve_submission(submission_id, admin_wallet)
                )
            elif platform == 'twitter':
                from twitter_task.twitter_task import twitter_task_service
                result = loop.run_until_complete(
                    twitter_task_service.approve_submission(submission_id, admin_wallet)
                )
            else:
                return jsonify({"success": False, "error": "Invalid platform"}), 400

            # Log admin action
            if result.get('success'):
                log_admin_action(
                    admin_wallet=admin_wallet,
                    action_type=f"approve_{platform}_task",
                    action_details={"submission_id": submission_id}
                )

            return jsonify(result)
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"❌ Error approving task: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/daily-tasks/reject", methods=["POST"])
@admin_required
def reject_daily_task():
    """Reject a daily task submission (admin only)"""
    try:
        data = request.json
        submission_id = data.get('submission_id')
        platform = data.get('platform')  # 'telegram' or 'twitter'
        reason = data.get('reason', '')
        admin_wallet = session.get('wallet')

        if not submission_id or not platform:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            if platform == 'telegram':
                from telegram_task.telegram_task import telegram_task_service
                result = loop.run_until_complete(
                    telegram_task_service.reject_submission(submission_id, admin_wallet, reason)
                )
            elif platform == 'twitter':
                from twitter_task.twitter_task import twitter_task_service
                result = loop.run_until_complete(
                    twitter_task_service.reject_submission(submission_id, admin_wallet, reason)
                )
            else:
                return jsonify({"success": False, "error": "Invalid platform"}), 400

            # Log admin action
            if result.get('success'):
                log_admin_action(
                    admin_wallet=admin_wallet,
                    action_type=f"reject_{platform}_task",
                    action_details={"submission_id": submission_id, "reason": reason}
                )

            return jsonify(result)
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"❌ Error rejecting task: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/api/admin/quiz-questions/upload", methods=["POST"])
@admin_required
def upload_quiz_questions():
    """Upload quiz questions from TXT file (admin only)"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400

        if not file.filename.endswith('.txt'):
            return jsonify({"success": False, "error": "File must be .txt format"}), 400

        # Read file content
        content = file.read().decode('utf-8')

        # Parse questions from TXT content
        questions = []
        current_question = {}
        parse_errors = []
        line_number = 0

        for line in content.split('\n'):
            line_number += 1
            line = line.strip()

            if not line:
                # Empty line - end of question
                if current_question:
                    # Check if all required fields are present
                    required_fields = ['question_id', 'question', 'answer_a', 'answer_b', 'answer_c', 'answer_d', 'correct']
                    missing_fields = [f for f in required_fields if f not in current_question]

                    if missing_fields:
                        parse_errors.append(f"Question at line ~{line_number}: Missing fields: {', '.join(missing_fields)}")
                    else:
                        questions.append(current_question)
                    current_question = {}
                continue

            if line.startswith('QUESTION_ID:'):
                current_question['question_id'] = line.replace('QUESTION_ID:', '').strip()
            elif line.startswith('QUESTION:'):
                current_question['question'] = line.replace('QUESTION:', '').strip()
            elif line.startswith('A)') or line.startswith('A:'):
                current_question['answer_a'] = line.replace('A)', '').replace('A:', '').strip()
            elif line.startswith('B)') or line.startswith('B:'):
                current_question['answer_b'] = line.replace('B)', '').replace('B:', '').strip()
            elif line.startswith('C)') or line.startswith('C:'):
                current_question['answer_c'] = line.replace('C)', '').replace('C:', '').strip()
            elif line.startswith('D)') or line.startswith('D:'):
                current_question['answer_d'] = line.replace('D)', '').replace('D:', '').strip()
            elif line.startswith('CORRECT:'):
                correct = line.replace('CORRECT:', '').strip().upper()
                if correct in ['A', 'B', 'C', 'D']:
                    current_question['correct'] = correct
                else:
                    parse_errors.append(f"Line {line_number}: Invalid correct answer '{correct}'. Must be A, B, C, or D")

        # Add last question if exists
        if current_question:
            required_fields = ['question_id', 'question', 'answer_a', 'answer_b', 'answer_c', 'answer_d', 'correct']
            missing_fields = [f for f in required_fields if f not in current_question]

            if missing_fields:
                parse_errors.append(f"Last question: Missing fields: {', '.join(missing_fields)}")
            else:
                questions.append(current_question)

        if not questions:
            example_format = """
Expected format (each question must have ALL fields):

QUESTION_ID: Q001
QUESTION: What is GoodDollar?
A: A cryptocurrency for UBI
B: A bank
C: A credit card
D: A website
CORRECT: A

(Empty line between questions)

QUESTION_ID: Q002
QUESTION: How often can you claim UBI?
A: Monthly
B: Daily
C: Yearly
D: Once
CORRECT: B
"""
            error_msg = "No valid questions found in file."
            if parse_errors:
                error_msg += f" Errors found: {'; '.join(parse_errors[:3])}"
            error_msg += f" Please check file format. {example_format}"

            return jsonify({
                "success": False,
                "error": error_msg,
                "parse_errors": parse_errors,
                "example_format": example_format
            }), 400

        # Insert questions into database
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        added_count = 0
        skipped_count = 0
        error_count = 0
        error_details = []

        admin_wallet = session.get("wallet")

        for q in questions:
            try:
                # Check if question_id already exists
                existing = safe_supabase_operation(
                    lambda: supabase.table('quiz_questions')\
                        .select('question_id')\
                        .eq('question_id', q['question_id'])\
                        .execute(),
                    fallback_result=type('obj', (object,), {'data': []})(),
                    operation_name="check question exists"
                )

                if existing.data and len(existing.data) > 0:
                    skipped_count += 1
                    logger.info(f"⚠️ Skipped duplicate question: {q['question_id']}")
                    continue

                # Add created_at timestamp
                from datetime import datetime
                q['created_at'] = datetime.utcnow().isoformat() + 'Z'

                # Insert question
                result = safe_supabase_operation(
                    lambda: supabase.table('quiz_questions').insert(q).execute(),
                    fallback_result=type('obj', (object,), {'data': []})(),
                    operation_name="insert question from file"
                )

                if result.data:
                    added_count += 1
                    logger.info(f"✅ Added question from file: {q['question_id']}")
                else:
                    error_count += 1
                    error_details.append(f"Failed to add {q['question_id']}")

            except Exception as e:
                error_count += 1
                error_details.append(f"{q.get('question_id', 'unknown')}: {str(e)}")
                logger.error(f"❌ Error adding question {q.get('question_id', 'unknown')}: {e}")

        # Log admin action
        log_admin_action(
            admin_wallet=admin_wallet,
            action_type="upload_quiz_questions",
            action_details={
                "total_questions": len(questions),
                "added": added_count,
                "skipped": skipped_count,
                "errors": error_count
            }
        )

        logger.info(f"✅ Quiz upload complete: {added_count} added, {skipped_count} skipped, {error_count} errors")

        return jsonify({
            "success": True,
            "total": len(questions),
            "added": added_count,
            "skipped": skipped_count,
            "errors": error_count,
            "error_details": error_details[:10]  # Limit to first 10 errors
        })

    except Exception as e:
        logger.error(f"❌ Upload quiz questions error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@routes.route("/admin")
@auth_required
def admin_dashboard():
    """Admin dashboard page"""
    wallet = session.get("wallet")

    from supabase_client import is_admin
    if not is_admin(wallet):
        logger.warning(f"⚠️ Non-admin access attempt from {wallet[:8]}...")
        return redirect("/dashboard")

    logger.info(f"✅ Admin access granted to {wallet[:8]}...")

    # Get username for display
    from supabase_client import supabase_logger
    username = supabase_logger.get_username(wallet)

    return render_template("admin_dashboard.html", wallet=wallet, username=username)


    return render_template("forum_post_detail.html",
                         wallet=wallet,
                         username=username, # Pass username to template
                         post=post,
                         categories=community_forum_service.categories)

@routes.route("/learn-earn")
def learn_earn_page():
    if not session.get("verified") or not session.get("wallet"):
        return redirect(url_for("routes.index"))

    wallet = session.get("wallet")
    # Check if user has set username, redirect to setup if not
    username = supabase_logger.get_username(wallet)
    if not username:
        return redirect(url_for("routes.setup_username"))

    # Track Learn & Earn page visit
    analytics.track_page_view(wallet, "learn_earn")

    return render_template("learn_and_earn.html",
                         wallet=wallet,
                         username=username) # Pass username to template

# --- New routes for username setup ---
@routes.route('/setup-username')
def setup_username():
    """Username setup page - ONE TIME ONLY"""
    wallet_address = session.get('wallet') or session.get('wallet_address')
    verified = session.get('verified') or session.get('ubi_verified')

    if not wallet_address or not verified:
        return redirect(url_for('routes.index'))

    # ALWAYS check database first for existing username (source of truth)
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()

        if supabase:
            # Direct database check for username
            result = supabase.table("user_data")\
                .select("username, wallet_address")\
                .eq("wallet_address", wallet_address)\
                .execute()

            logger.info(f"🔍 Database username check for {wallet_address[:8]}...: found {len(result.data) if result.data else 0} records")

            if result.data and len(result.data) > 0:
                username = result.data[0].get("username")
                logger.info(f"🔍 Database returned username: '{username}' (type: {type(username)})")

                # Check if username exists AND is not empty/null
                if username and str(username).strip() and username != 'None':
                    # Username already set in database
                    logger.info(f"✅ Username already exists for {wallet_address[:8]}...: {username}, redirecting to overview")

                    # Make sure it's also in session
                    session['username'] = username
                    session.permanent = True

                    # Redirect to overview
                    return redirect(url_for('routes.overview'))
                else:
                    logger.info(f"ℹ️ Username is empty/null for {wallet_address[:8]}..., showing setup page")
            else:
                logger.info(f"ℹ️ No user record found for {wallet_address[:8]}..., showing setup page")
        else:
            logger.warning(f"⚠️ Supabase not available for username check")

    except Exception as e:
        logger.error(f"❌ Error checking username in setup_username: {e}")
        import traceback
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")

    # No username yet, show setup page
    logger.info(f"ℹ️ Showing username setup page for {wallet_address[:8]}...")
    return render_template('setup_username.html', wallet_address=wallet_address)

@routes.route('/api/check-username', methods=['POST'])
def check_username():
    """Check if username is available"""
    data = request.get_json()
    username = data.get('username', '').strip()

    # Validate format
    if not username or len(username) < 3 or len(username) > 50:
        return jsonify({
            'valid': False,
            'message': 'Username must be 3-50 characters long'
        })

    # Check format (alphanumeric and underscore only)
    import re
    if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
        return jsonify({
            'valid': False,
            'message': 'Username can only contain letters, numbers, and underscores'
        })

    # Check availability using the imported or mocked supabase_logger
    available = supabase_logger.check_username_available(username)

    return jsonify({
        'valid': available,
        'message': 'Username is available!' if available else 'Username is already taken'
    })

@routes.route('/api/set-username', methods=['POST'])
def set_username():
    """Set username for user - ONE TIME SETUP ONLY"""
    data = request.get_json()
    wallet_address = data.get('wallet_address')
    username = data.get('username', '').strip()

    # Verify session integrity
    if not wallet_address or wallet_address != session.get('wallet'):
        return jsonify({'success': False, 'error': 'Invalid session or wallet mismatch'}), 401

    if not username:
        return jsonify({'success': False, 'error': 'Username is required'}), 400

    # CRITICAL: Check database FIRST if username already set (prevent multiple changes)
    existing_username = supabase_logger.get_username(wallet_address)
    if existing_username:
        logger.warning(f"⚠️ Attempt to set username again for {wallet_address[:8]}... (already has: {existing_username})")
        return jsonify({
            'success': False,
            'error': f'Username already set to "{existing_username}". You can only set your username once.',
            'current_username': existing_username
        }), 400

    # Use the imported or mocked supabase_logger to set username
    result = supabase_logger.set_username(wallet_address, username)

    if result.get('success'):
        # IMPORTANT: Store username in session permanently
        session['username'] = username
        session.permanent = True

        # Log the username setup
        logger.info(f"✅ Username set for {wallet_address[:8]}...: {username}")

        # Track analytics (only 2 params: wallet and page)
        analytics.track_page_view(wallet_address, "username_setup_completed")

        return jsonify({
            'success': True,
            'username': username,
            'message': 'Username set successfully!'
        })
    else:
        # Return the error from supabase_logger (e.g., username taken)
        return jsonify(result), 400



# --- End of new routes ---


@routes.route('/api/p2p/history')
def get_p2p_history_api():
    """P2P trading has been removed - return empty history"""
    try:
        wallet = session.get('wallet')
        if not wallet or not session.get('verified'):
            return jsonify({"success": False, "error": "Not authenticated"}), 401

        logger.info(f"📋 P2P trading disabled - returning empty history for {wallet[:8]}...")

        return jsonify({
            "success": True,
            "trades": [],
            "total": 0,
            "message": "P2P trading feature has been disabled"
        })

    except Exception as e:
        logger.error(f"❌ Error in P2P history endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "trades": [],
            "total": 0
        }), 500

@routes.route("/api/admin/community-stories-notifications", methods=["GET"])
@admin_required
def get_admin_notifications():
    """Get pending submissions for admin"""
    try:
        wallet = session.get("wallet")

        supabase = get_supabase_client()
        if not supabase:
            return jsonify({"success": False, "error": "Database not available"}), 500

        # Get pending submissions directly to include storage_path
        pending = safe_supabase_operation(
            lambda: supabase.table('community_stories_submissions')\
                .select('*')\
                .eq('status', 'pending')\
                .order('submitted_at', desc=True)\
                .execute(),
            fallback_result=type('obj', (object,), {'data': []})(),
            operation_name="get pending community stories"
        )

        # Format for admin display
        notifications = []
        if pending.data:
            for sub in pending.data:
                notifications.append({
                    'submission_id': sub.get('submission_id'),
                    'community_stories_submissions': sub
                })

        return jsonify({
            "success": True,
            "notifications": notifications,
            "count": len(notifications)
        })

    except Exception as e:
        logger.error(f"❌ Error getting admin notifications: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
