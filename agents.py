from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.tools import tool
from prompts import (
    ORCHESTRATOR_PROMPT, 
    VERIFICATION_PROMPT, 
    EMI_REMINDER_PROMPT,
    PAYMENT_COLLECTION_PROMPT,
    PAYMENT_PLAN_PROMPT,
    ESCALATION_PROMPT
)
from tools import (
    verify_customer_identity,
    get_emi_details,
    check_overdue_status,
    generate_payment_link,
    create_payment_plan,
    create_escalation_ticket
)
from data import ConversationMessage, ConversationState, CUSTOMER_DB
from typing import Dict
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key,temperature=0.1)

# Verification Agent Tools
verification_tools = [verify_customer_identity]

# EMI Reminder Agent Tools  
emi_reminder_tools = [get_emi_details, check_overdue_status]

# Payment Collection Agent Tools
payment_collection_tools = [generate_payment_link]

# Payment Plan Agent Tools
payment_plan_tools = [create_payment_plan]

# Escalation Agent Tools
escalation_tools = [create_escalation_ticket]

# Create sub-agent tools for orchestrator
@tool
def call_verification_agent(customer_phone: str, task: str, verification_data: str = "") -> str:
    """Call verification agent to handle customer identity verification tasks."""
    verification_agent = create_tool_calling_agent(llm, verification_tools, VERIFICATION_PROMPT)
    verification_executor = AgentExecutor(agent=verification_agent, tools=verification_tools, verbose=False)
    
    input_data = {
        "input": f"Task: {task}. Verification data: {verification_data}",
        "customer_phone": customer_phone
    }
    
    try:
        print(f"Calling verification agent with input: {input_data}")
        result = verification_executor.invoke(input_data)
        return result.get("output", "Verification agent completed the task.")
    except Exception as e:
        return f"Verification agent error: {str(e)}"

@tool
def call_emi_reminder_agent(customer_phone: str, task: str) -> str:
    """Call EMI reminder agent to handle payment reminders and due date information."""
    emi_agent = create_tool_calling_agent(llm, emi_reminder_tools, EMI_REMINDER_PROMPT)
    emi_executor = AgentExecutor(agent=emi_agent, tools=emi_reminder_tools, verbose=False)
    
    input_data = {
        "input": f"Task: {task}",
        "customer_phone": customer_phone
    }
    
    try:
        print(f"Calling EMI reminder agent with input: {input_data}")
        result = emi_executor.invoke(input_data)
        return result.get("output", "EMI reminder agent completed the task.")
    except Exception as e:
        return f"EMI reminder agent error: {str(e)}"

@tool
def call_payment_collection_agent(customer_phone: str, task: str, amount: float = 0, payment_method: str = "") -> str:
    """Call payment collection agent to handle payment processing and link generation."""
    payment_agent = create_tool_calling_agent(llm, payment_collection_tools, PAYMENT_COLLECTION_PROMPT)
    payment_executor = AgentExecutor(agent=payment_agent, tools=payment_collection_tools, verbose=False)
    
    input_data = {
        "input": f"Task: {task}. Amount: {amount}. Payment method: {payment_method}",
        "customer_phone": customer_phone
    }
    
    try:
        print(f"Calling payment collection agent with input: {input_data}")
        result = payment_executor.invoke(input_data)
        return result.get("output", "Payment collection agent completed the task.")
    except Exception as e:
        return f"Payment collection agent error: {str(e)}"

@tool  
def call_payment_plan_agent(customer_phone: str, task: str, monthly_amount: float = 0, start_date: str = "") -> str:
    """Call payment plan agent to handle payment plan creation and options."""
    plan_agent = create_tool_calling_agent(llm, payment_plan_tools, PAYMENT_PLAN_PROMPT)
    plan_executor = AgentExecutor(agent=plan_agent, tools=payment_plan_tools, verbose=False)
    
    input_data = {
        "input": f"Task: {task}. Monthly amount: {monthly_amount}. Start date: {start_date}",
        "customer_phone": customer_phone
    }
    
    try:
        print(f"Calling payment plan agent with input: {input_data}")
        result = plan_executor.invoke(input_data)
        return result.get("output", "Payment plan agent completed the task.")
    except Exception as e:
        return f"Payment plan agent error: {str(e)}"

@tool
def call_escalation_agent(customer_phone: str, reason: str, details: str) -> str:
    """Call escalation agent to handle customer escalations and logging."""
    escalation_agent = create_tool_calling_agent(llm, escalation_tools, ESCALATION_PROMPT)
    escalation_executor = AgentExecutor(agent=escalation_agent, tools=escalation_tools, verbose=False)
    
    input_data = {
        "input": f"Escalation reason: {reason}. Details: {details}",
        "customer_phone": customer_phone
    }
    
    try:
        print(f"Calling escalation agent with input: {input_data}")
        result = escalation_executor.invoke(input_data)
        return result.get("output", "Escalation agent completed the task.")
    except Exception as e:
        return f"Escalation agent error: {str(e)}"

# Orchestrator tools 
orchestrator_tools = [
    call_verification_agent,
    call_emi_reminder_agent, 
    call_payment_collection_agent,
    call_payment_plan_agent,
    call_escalation_agent
]

def create_orchestrator_agent():
    """Create the main orchestrator agent."""
    orchestrator = create_tool_calling_agent(llm, orchestrator_tools, ORCHESTRATOR_PROMPT)
    orchestrator_executor = AgentExecutor(
        agent=orchestrator, 
        tools=orchestrator_tools, 
        verbose=True,
        max_iterations=10,  
        handle_parsing_errors=True
    )
    return orchestrator_executor

class LoanAdvisorSystem:
    def __init__(self):
        self.orchestrator = create_orchestrator_agent()
        self.conversation_states: Dict[str, ConversationState] = {}
    
    def start_conversation(self, customer_phone: str) -> str:
        """Start a new conversation with a customer."""
        # Initialize conversation state
        state = ConversationState(
            customer_phone=customer_phone,
            current_step="initial"
        )
        self.conversation_states[customer_phone] = state
        
        # Get customer info for greeting
        customer = CUSTOMER_DB.get(customer_phone)
        
        if not customer:
            return f"I'm sorry, but I couldn't find a customer record for the phone number {customer_phone}. Please contact our customer service team for assistance."
        # Store customer in state
        state.customer = customer

        # Initial greeting with name verification
        greeting = f"Hello, this is your loan advisor from ABC Financial Services. Are we speaking with {customer.full_name}?"
        state.current_step = "name_verification"

        # Add initial message to conversation history
        self._add_message_to_history(customer_phone, "assistant", greeting, "name_verification")
        return greeting
    
    def continue_conversation(self, customer_phone: str, user_input: str) -> str:
        """Continue an existing conversation."""
        if customer_phone not in self.conversation_states:
            return "I'm sorry, but I don't have an active conversation for this number. Please restart the call."
        
        state = self.conversation_states[customer_phone]
        state.user_response = user_input
        
        # Add user message to conversation history
        self._add_message_to_history(customer_phone, "user", user_input, state.current_step)
        
        # Format conversation history for context
        formatted_history = self._format_conversation_history(customer_phone)
        
        # Prepare input for orchestrator with full context
        conversation_context = {
            "input": user_input,
            "customer_phone": customer_phone,
            "conversation_state": {
                "current_step": state.current_step,
                "verification_status": state.verification_status,
                "max_attempts": state.max_verification_attempts,
                "escalation_needed": state.escalation_needed,
                "customer_name": state.customer.full_name if state.customer else "Unknown",
                "customer_balance": state.customer.current_balance if state.customer else 0,
                "next_emi_amount": state.customer.next_emi_amount if state.customer else 0,
                "next_due_date": state.customer.next_due_date if state.customer else ""
            },
            "conversation_history": formatted_history
        }
        
        try:
            print("Calling orchestrator with context:", conversation_context)
            result = self.orchestrator.invoke(conversation_context)
            response = result.get("output", "I apologize, but I'm having trouble processing your request right now.")

            # Add AI response to conversation history
            self._add_message_to_history(customer_phone, "assistant", response, state.current_step)
            return response
            
        except Exception as e:
            error_msg = f"I apologize for the technical difficulty. Please contact our customer service team. Error: {str(e)}"
            self._add_message_to_history(customer_phone, "assistant", error_msg, "error")
            return error_msg
    def _add_message_to_history(self, customer_phone: str, role: str, content: str, step: str = ""):
        """Add a message to the conversation history."""
        if customer_phone not in self.conversation_states:
            return
        
        state = self.conversation_states[customer_phone]
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            step=step
        )
        state.conversation_history.append(message)
        
        # Update context summary periodically
        if len(state.conversation_history) % 4 == 0:  # Every 4 messages
            self._update_context_summary(customer_phone)

    def _format_conversation_history(self, customer_phone: str, max_messages: int = 10) -> str:
        """Format conversation history for the orchestrator."""
        if customer_phone not in self.conversation_states:
            return ""
        
        state = self.conversation_states[customer_phone]
        # Get recent messages (limit to prevent token overflow)
        recent_messages = state.conversation_history[-max_messages:]
        
        formatted = []
        for msg in recent_messages:
            role_prefix = "AI" if msg.role == "assistant" else "Customer"
            step_info = f" [{msg.step}]" if msg.step else ""
            formatted.append(f"{role_prefix}{step_info}: {msg.content}")
        
        return "\n".join(formatted)
    
    def _update_context_summary(self, customer_phone: str):
        """Update context summary of the conversation."""
        if customer_phone not in self.conversation_states:
            return
        
        state = self.conversation_states[customer_phone]
        
        # Create a simple context summary
        summary_parts = []
        
        if state.verification_status == "verified":
            summary_parts.append("Customer identity verified")
        elif state.verification_status == "failed":
            summary_parts.append("Customer verification failed")
        
        if state.current_step == "emi_reminder":
            summary_parts.append("EMI reminder provided")
        elif state.current_step == "payment_collection":
            summary_parts.append("Payment collection in progress")
        elif state.current_step == "payment_plan":
            summary_parts.append("Payment plan discussion")
        
        if state.escalation_needed:
            summary_parts.append("Escalation required")
        
        state.context_summary = " | ".join(summary_parts)
    
    def end_conversation(self, customer_phone: str):
        """End and cleanup conversation."""
        if customer_phone in self.conversation_states:
            del self.conversation_states[customer_phone]