from dataclasses import dataclass
from typing import Optional

@dataclass
class Customer:
    customer_id: str
    full_name: str
    phone: str
    date_of_birth: str
    ssn_last_four: str
    loan_number: str
    current_balance: float
    next_emi_amount: float
    next_due_date: str
    late_fee: float
    interest_rate: float

@dataclass
class ConversationMessage:
    role: str  # "user", "assistant"
    content: str
    timestamp: str
    step: str = ""

@dataclass
class ConversationState:
    customer_phone: str
    customer: Optional[Customer] = None
    verification_status: str = "pending"  # pending, verified, failed
    current_step: str = "initial"  # initial, name_verification, ssn_verification, emi_reminder, payment_collection, etc.
    max_verification_attempts: int = 1
    user_response: str = ""
    escalation_needed: bool = False
    conversation_complete: bool = False
    conversation_history: list = None
    context_summary: str = ""
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
            
# Sample customer database
CUSTOMER_DB = {
    "+917008817812": Customer(
        customer_id="CUST001",
        full_name="Swastik Kumar Sahu",
        phone="+917008817812",
        date_of_birth="1985-06-15",
        ssn_last_four="1234",
        loan_number="LN001234",
        current_balance=15000.0,
        next_emi_amount=750.0,
        next_due_date="2025-06-28",
        late_fee=50.0,
        interest_rate=12.5
    ),
    "+1234567891": Customer(
        customer_id="CUST002",
        full_name="Sarah Johnson",
        phone="+1234567891",
        date_of_birth="1990-03-22",
        ssn_last_four="5678",
        loan_number="LN005678",
        current_balance=8500.0,
        next_emi_amount=425.0,
        next_due_date="2025-07-20",
        late_fee=35.0,
        interest_rate=11.0
    ),
    "+1234567892": Customer(
        customer_id="CUST003",
        full_name="Mike Davis",
        phone="+1234567892",
        date_of_birth="1988-11-10",
        ssn_last_four="9012",
        loan_number="LN009012",
        current_balance=22000.0,
        next_emi_amount=1100.0,
        next_due_date="2025-06-18",
        late_fee=75.0,
        interest_rate=13.0
    )
}