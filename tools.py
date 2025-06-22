from langchain_core.tools import tool
from typing import Dict, Any
from data import CUSTOMER_DB, Customer, ConversationState
import random
from datetime import datetime, timedelta

# Verification Agent Tools

@tool
def verify_customer_identity(phone: str, verification_data: str) -> Dict[str, Any]:
    """Verify customer identity using SSN last 4 digits."""
    customer = CUSTOMER_DB.get(phone)
    if not customer:
        return {"success": False, "message": "Customer not found"}

    if verification_data == customer.ssn_last_four:
        return {"success": True, "message": "Customer identity verified successfully"}
    
    return {"success": False, "message": "Verification failed. Information does not match our records"}

# EMI Reminder Agent Tools
@tool
def get_emi_details(phone: str) -> Dict[str, Any]:
    """Get EMI details for the customer."""
    customer = CUSTOMER_DB.get(phone)
    if not customer:
        return {"success": False, "message": "Customer not found"}
    
    return {
        "success": True,
        "emi_details": {
            "next_emi_amount": customer.next_emi_amount,
            "next_due_date": customer.next_due_date,
            "current_balance": customer.current_balance,
            "loan_number": customer.loan_number,
            "late_fee": customer.late_fee,
            "interest_rate": customer.interest_rate
        }
    }

@tool
def check_overdue_status(phone: str) -> Dict[str, Any]:
    """Check if customer has any overdue payments."""
    customer = CUSTOMER_DB.get(phone)
    if not customer:
        return {"success": False, "message": "Customer not found"}
    
    due_date = datetime.strptime(customer.next_due_date, "%Y-%m-%d")
    current_date = datetime.now()
    
    is_overdue = due_date < current_date
    days_overdue = (current_date - due_date).days if is_overdue else 0
    
    return {
        "success": True,
        "is_overdue": is_overdue,
        "days_overdue": days_overdue,
        "overdue_amount": customer.next_emi_amount if is_overdue else 0
    }

# Payment Collection Agent Tools
@tool
def generate_payment_link(phone: str, amount: float) -> Dict[str, Any]:
    """Generate a secure payment link for the customer. Works for any payment method."""
    customer = CUSTOMER_DB.get(phone)
    if not customer:
        return {"success": False, "message": "Customer not found"}
    
    # Generate a dummy payment link
    payment_id = f"PAY_{customer.customer_id}_{random.randint(1000, 9999)}"
    payment_link = f"Link {payment_id}"
    
    return {
        "success": True,
        "payment_link": payment_link,
        "payment_id": payment_id,
        "amount": amount,
        "expiry_time": "10 minutes"
    }


# Payment Plan Agent Tools
@tool
def create_payment_plan(phone: str, monthly_amount: float, start_date: str) -> Dict[str, Any]:
    """Create a payment plan for the customer."""
    customer = CUSTOMER_DB.get(phone)
    if not customer:
        return {"success": False, "message": "Customer not found"}
    
    # Calculate plan details
    remaining_balance = customer.current_balance
    months_needed = months_needed = int(remaining_balance / monthly_amount) + (1 if remaining_balance % monthly_amount > 0 else 0)
    
    plan_id = f"PLAN_{customer.customer_id}_{random.randint(1000, 9999)}"
    
    return {
        "success": True,
        "plan_id": plan_id,
        "monthly_amount": monthly_amount,
        "start_date": start_date,
        "total_months": months_needed,
        "total_amount": remaining_balance,
        "estimated_completion": "Based on monthly payments"
    }

# Escalation Agent Tools
@tool
def create_escalation_ticket(phone: str, reason: str, details: str) -> Dict[str, Any]:
    """Create an escalation ticket for human intervention."""
    customer = CUSTOMER_DB.get(phone)
    if not customer:
        return {"success": False, "message": "Customer not found"}
    
    ticket_id = f"ESC_{random.randint(10000, 99999)}"
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "priority": "high" if "verification" in reason.lower() else "medium",
        "estimated_response": "20 minutes",
        "message": f"Escalation ticket {ticket_id} created successfully"
    }
