import base64
import json
import logging
import requests
import datetime
from config import current_config

logger = logging.getLogger(__name__)

class MPesaAPI:
    def __init__(self):
        self.consumer_key = current_config.MPESA_CONSUMER_KEY
        self.consumer_secret = current_config.MPESA_CONSUMER_SECRET
        self.api_url = current_config.MPESA_API_URL
        self.shortcode = current_config.MPESA_SHORTCODE
        self.passkey = current_config.MPESA_PASSKEY
        self.callback_url = current_config.MPESA_CALLBACK_URL
        self.access_token = None
        self.access_token_expiry = None
    
    def generate_access_token(self):
        """Generate OAuth access token for M-Pesa API"""
        try:
            url = f"{self.api_url}/oauth/v1/generate?grant_type=client_credentials"
            auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode("utf-8")
            headers = {
                "Authorization": f"Basic {auth}"
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"M-Pesa access token request failed: {response.text}")
                return False
                
            result = response.json()
            self.access_token = result.get("access_token")
            # Set expiry to 50 minutes from now (tokens usually valid for 1 hour)
            self.access_token_expiry = datetime.datetime.now() + datetime.timedelta(minutes=50)
            
            return True
        except Exception as e:
            logger.error(f"Error generating M-Pesa access token: {e}")
            return False
    
    def get_access_token(self):
        """Get access token, generating a new one if necessary"""
        if not self.access_token or not self.access_token_expiry or self.access_token_expiry < datetime.datetime.now():
            if not self.generate_access_token():
                return None
        
        return self.access_token
    
    def generate_timestamp(self):
        """Generate timestamp in the format required by M-Pesa API"""
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    def generate_password(self, timestamp):
        """Generate password for M-Pesa API"""
        data_to_encode = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(data_to_encode.encode()).decode("utf-8")
    
    def initiate_stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate STK push to user's phone for payment"""
        token = self.get_access_token()
        if not token:
            return {
                "success": False,
                "message": "Failed to get access token"
            }
        
        try:
            # Remove any country code (e.g., +254) and ensure number starts with 254
            if phone_number.startswith("+"):
                phone_number = phone_number[1:]
            if phone_number.startswith("0"):
                phone_number = "254" + phone_number[1:]
            elif not phone_number.startswith("254"):
                phone_number = "254" + phone_number
            
            timestamp = self.generate_timestamp()
            password = self.generate_password(timestamp)
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone_number,
                "PartyB": self.shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": self.callback_url,
                "AccountReference": account_reference,
                "TransactionDesc": transaction_desc
            }
            
            url = f"{self.api_url}/mpesa/stkpush/v1/processrequest"
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"STK push request failed: {response.text}")
                return {
                    "success": False,
                    "message": f"Failed to initiate payment: {response.text}"
                }
            
            result = response.json()
            
            if "ResponseCode" in result and result["ResponseCode"] == "0":
                return {
                    "success": True,
                    "checkout_request_id": result.get("CheckoutRequestID"),
                    "message": "STK push initiated successfully"
                }
            else:
                logger.error(f"STK push failed: {result}")
                return {
                    "success": False,
                    "message": f"Failed to initiate payment: {result.get('ResponseDescription', 'Unknown error')}"
                }
        except Exception as e:
            logger.error(f"Error initiating STK push: {e}")
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}"
            }
    
    def check_payment_status(self, checkout_request_id):
        """Check the status of an STK push payment"""
        token = self.get_access_token()
        if not token:
            return {
                "success": False,
                "message": "Failed to get access token"
            }
        
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            timestamp = self.generate_timestamp()
            password = self.generate_password(timestamp)
            
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            url = f"{self.api_url}/mpesa/stkpushquery/v1/query"
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Payment status check failed: {response.text}")
                return {
                    "success": False,
                    "message": f"Failed to check payment status: {response.text}"
                }
            
            result = response.json()
            
            if "ResultCode" in result:
                if result["ResultCode"] == "0":
                    return {
                        "success": True,
                        "paid": True,
                        "message": "Payment completed successfully"
                    }
                else:
                    return {
                        "success": True,
                        "paid": False,
                        "message": result.get("ResultDesc", "Payment failed or is pending")
                    }
            else:
                logger.error(f"Unexpected payment status response: {result}")
                return {
                    "success": False,
                    "message": "Invalid response from M-Pesa"
                }
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}"
            }
    
    def process_callback(self, callback_data):
        """Process callback data from M-Pesa"""
        try:
            body = callback_data.get("Body", {})
            stkCallback = body.get("stkCallback", {})
            result_code = stkCallback.get("ResultCode")
            
            if result_code != 0:
                return {
                    "success": False,
                    "message": stkCallback.get("ResultDesc", "Payment failed")
                }
            
            # Extract payment details
            checkout_request_id = stkCallback.get("CheckoutRequestID")
            metadata = stkCallback.get("CallbackMetadata", {})
            items = metadata.get("Item", [])
            
            payment_info = {}
            for item in items:
                name = item.get("Name")
                value = item.get("Value")
                
                if name == "Amount":
                    payment_info["amount"] = value
                elif name == "MpesaReceiptNumber":
                    payment_info["receipt_number"] = value
                elif name == "PhoneNumber":
                    payment_info["phone_number"] = value
                elif name == "TransactionDate":
                    payment_info["transaction_date"] = value
            
            return {
                "success": True,
                "checkout_request_id": checkout_request_id,
                "payment_info": payment_info
            }
        except Exception as e:
            logger.error(f"Error processing M-Pesa callback: {e}")
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}"
            }

# Create a singleton instance
mpesa = MPesaAPI()
