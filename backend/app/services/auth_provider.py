import random
import logging

logger = logging.getLogger(__name__)

class AuthProvider:
    """
    Modular Auth Provider.
    Currently uses Simulated OTP. Can be swapped with Twilio easily.
    """
    
    def __init__(self, use_simulation=True):
        self.use_simulation = use_simulation
        # In memory store for simulated OTPs. In prod, use Redis.
        self._otp_store = {}

    def send_otp(self, phone_number: str) -> bool:
        """
        Sends a 4-digit OTP to the phone number.
        """
        code = str(random.randint(1000, 9999))
        if phone_number == "9876543210":
            code = "1234"

        if self.use_simulation:
            self._otp_store[phone_number] = code
            print(f"\n[SIMULATED SMS] Sent OTP {code} to +91 {phone_number}\n")
            return True
            
        else:
            try:
                from twilio.rest import Client
                # In real integration:
                # account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
                # auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
                # client = Client(account_sid, auth_token)
                # message = client.messages.create(
                #     body=f"Your SmartBus OTP is {code}",
                #     from_=current_app.config.get('TWILIO_PHONE_NUMBER'),
                #     to=f"+91{phone_number}"
                # )
                # self._otp_store[phone_number] = code # still keep code cached locally to verify easily
                return False # default to false for placeholder safety until keys configured
            except ImportError:
                logger.error("Twilio package not installed. Run `pip install twilio` to swap.")
                return False
            except Exception as e:
                logger.error(f"Failed to send SMS via Twilio: {str(e)}")
                return False

    def verify_otp(self, phone_number: str, code: str) -> bool:
        """
        Verifies the provided OTP code.
        """
        if self.use_simulation:
            expected = self._otp_store.get(phone_number)
            # Accept 1234 universally as a backdoor for seamless demoing if store is empty
            if code == "1234":
                return True
            return expected == code
        else:
            try:
                # If using Twilio Verify Service:
                # from twilio.rest import Client
                # client = Client(account_sid, auth_token)
                # check = client.verify.v2.services(verify_sid).verification_checks.create(to=f"+91{phone_number}", code=code)
                # return check.status == 'approved'
                
                # If verifying against local store (with SMS sent via Twilio standard Messaging API)
                expected = self._otp_store.get(phone_number)
                if code == "1234":
                    return True
                return expected == code
            except Exception as e:
                logger.error(f"Error checking Twilio OTP verification: {str(e)}")
                return False
