import time
import uuid
import datetime
import logging

logger = logging.getLogger(__name__)

class PaymentProvider:
    """
    Modular Payment Provider.
    Currently simulates Secure Gateway validation. Can be swapped with Stripe.
    """
    
    def __init__(self, use_simulation=True):
        self.use_simulation = use_simulation

    def _luhn_check(self, card_num: str) -> bool:
        card_num = card_num.replace(" ", "").replace("-", "")
        if not card_num.isdigit():
            return False
        total = 0
        num_digits = len(card_num)
        oddeven = num_digits & 1
        for count in range(num_digits):
            digit = int(card_num[count])
            if not ((count & 1) ^ oddeven):
                digit = digit * 2
                if digit > 9:
                    digit = digit - 9
            total += digit
        return (total % 10) == 0

    def process_card_payment(self, amount: float, card_number: str, cvv: str, expiry: str) -> dict:
        """
        Simulates processing a credit card with Luhn checksum validation and expiry verification.
        """
        if self.use_simulation:
            # 1. Basic length checks
            card_number = card_number.replace(' ', '')
            if len(card_number) < 13 or len(card_number) > 19:
                return {"success": False, "error": "Invalid card length"}
                
            if len(cvv) < 3 or len(cvv) > 4:
                return {"success": False, "error": "Invalid CVV (must be 3 or 4 digits)"}
                
            # 2. Luhn Checksum validation
            if not self._luhn_check(card_number):
                return {"success": False, "error": "Card number failed Luhn checksum check (invalid card)"}

            # 3. Expiry validation (MM/YY)
            if '/' not in expiry:
                return {"success": False, "error": "Invalid expiry date format. Use MM/YY"}
            try:
                parts = expiry.split('/')
                exp_month = int(parts[0])
                exp_year = int(parts[1])
                if exp_month < 1 or exp_month > 12:
                    return {"success": False, "error": "Invalid expiry month (must be 1-12)"}
                
                # Convert YY to YYYY
                if exp_year < 100:
                    exp_year += 2000
                    
                now = datetime.datetime.now()
                # Expiration happens at the end of the month
                if exp_month == 12:
                    exp_date = datetime.datetime(exp_year + 1, 1, 1) - datetime.timedelta(days=1)
                else:
                    exp_date = datetime.datetime(exp_year, exp_month + 1, 1) - datetime.timedelta(days=1)
                    
                if exp_date < now:
                    return {"success": False, "error": "Card has expired"}
            except ValueError:
                return {"success": False, "error": "Invalid expiry month/year digits"}
            except Exception as e:
                return {"success": False, "error": f"Invalid expiry date format: {str(e)}"}
                
            # Simulate processing delay
            time.sleep(1.0)
            
            # Simulate success
            transaction_id = f"txn_sim_{uuid.uuid4().hex[:12]}"
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": "succeeded"
            }
        else:
            try:
                import stripe
                # In real integration, Stripe PaymentIntent or Token charge:
                # stripe.api_key = "sk_test_..." (configure via app config)
                # intent = stripe.PaymentIntent.create(
                #     amount=int(amount * 100), # amount in cents/paise
                #     currency='inr',
                #     payment_method_data={
                #         "type": "card",
                #         "card": {
                #             "number": card_number,
                #             "cvc": cvv,
                #             "exp_month": int(expiry.split('/')[0]),
                #             "exp_year": int(expiry.split('/')[1]) + 2000 if len(expiry.split('/')[1]) == 2 else int(expiry.split('/')[1]),
                #         }
                #     },
                #     confirm=True,
                #     off_session=True
                # )
                # return {"success": True, "transaction_id": intent.id, "status": intent.status}
                return {"success": False, "error": "Real Stripe gateway credentials are not configured"}
            except ImportError:
                logger.error("Stripe SDK is not installed. Run `pip install stripe` to swap.")
                return {"success": False, "error": "Stripe SDK package is missing on the server"}
            except Exception as e:
                return {"success": False, "error": f"Stripe gateway transaction error: {str(e)}"}
            
    def process_upi_payment(self, amount: float, upi_id: str) -> dict:
        if self.use_simulation:
            if '@' not in upi_id or len(upi_id.split('@')[0]) == 0 or len(upi_id.split('@')[1]) == 0:
                return {"success": False, "error": "Invalid UPI VPA ID format"}
            time.sleep(0.8)
            return {
                "success": True,
                "transaction_id": f"upi_sim_{uuid.uuid4().hex[:12]}",
                "status": "succeeded"
            }
        
        # Real UPI integrations (like UPI deep-linking via Razorpay/PhonePe)
        return {"success": False, "error": "Real UPI payment gateway integration is not configured"}
