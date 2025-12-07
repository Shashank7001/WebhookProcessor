import hmac
import hashlib
from typing import Optional, Tuple

def calculate_hmac_signature(raw_body: bytes, secret: str) -> str:
    
    secret_bytes = secret.encode('utf-8')
    
    computed_hmac = hmac.new(
        key=secret_bytes, 
        msg=raw_body, 
        digestmod=hashlib.sha256
    )
    
    return f"sha256={computed_hmac.hexdigest()}"


def verify_hmac_signature(
    raw_body: bytes, 
    x_signature: Optional[str], 
    secret: str
):

    expected_signature = calculate_hmac_signature(raw_body, secret)
    
    if not x_signature:
        return False, expected_signature

    is_valid = hmac.compare_digest(expected_signature, x_signature)
    
    return is_valid, expected_signature