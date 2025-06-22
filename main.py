import os
from dotenv import load_dotenv
from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import threading
import time
from typing import Optional, Dict
from agents import LoanAdvisorSystem
from data import CUSTOMER_DB

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'your_account_sid_here')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'your_auth_token_here')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '+1234567890')  
NGROK_URL = os.getenv('NGROK_URL', 'https://your-ngrok-url.ngrok.io')  

app = Flask(__name__)

class CallState:
    def __init__(self):
        self.active_calls: Dict[str, dict] = {}
        self.advisor_system = LoanAdvisorSystem()
    
    def start_call(self, call_sid: str, customer_phone: str):
        """Initialize a new call state"""
        self.active_calls[call_sid] = {
            'customer_phone': customer_phone,
            'conversation_started': False,
            'turn_count': 0,
            'max_turns': 20
        }
    
    def get_call_state(self, call_sid: str):
        """Get call state by call SID"""
        return self.active_calls.get(call_sid)
    
    def end_call(self, call_sid: str):
        """Clean up call state"""
        if call_sid in self.active_calls:
            customer_phone = self.active_calls[call_sid]['customer_phone']
            self.advisor_system.end_conversation(customer_phone)
            del self.active_calls[call_sid]

call_state = CallState()

def make_outbound_call(customer_phone: str) -> bool:
    """Make an outbound call to a customer"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        call = client.calls.create(
            to=customer_phone,
            from_=TWILIO_PHONE_NUMBER,
            url=f'{NGROK_URL}/voice/start',
            method='POST',
            status_callback=f'{NGROK_URL}/voice/status',
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            status_callback_method='POST'
        )
        
        print(f"📞 Outbound call initiated to {customer_phone}")
        print(f"📋 Call SID: {call.sid}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to make call: {str(e)}")
        return False

@app.route('/voice/start', methods=['POST'])
def voice_start():
    """Handle the initial call connection and start conversation"""
    response = VoiceResponse()

    call_sid = request.form.get('CallSid')
    to_number = request.form.get('To')  
    
    print(f"📞 Call connected - SID: {call_sid}, To: {to_number}")

    call_state.start_call(call_sid, to_number)

    try:
        initial_message = call_state.advisor_system.start_conversation(to_number)
        call_state.active_calls[call_sid]['conversation_started'] = True
        
        response.say(initial_message, voice='alice', language='en-US')

        gather = response.gather(
            input='speech',
            timeout=10,
            speech_timeout='auto',
            action=f'{NGROK_URL}/voice/process',
            method='POST'
        )

        response.say("I didn't hear anything. Let me try again.", voice='alice')
        response.redirect(f'{NGROK_URL}/voice/process')
        
    except Exception as e:
        print(f"❌ Error in voice_start: {str(e)}")
        response.say("I'm sorry, there was an error starting our conversation. Please try again later.")
        response.hangup()
    
    return Response(str(response), mimetype='text/xml')

@app.route('/voice/process', methods=['POST'])
def voice_process():
    """Process user speech input and generate AI response"""
    response = VoiceResponse()
    
    call_sid = request.form.get('CallSid')
    speech_result = request.form.get('SpeechResult', '').strip()
    
    print(f"🎤 User said: '{speech_result}' (Call: {call_sid})")
    
    call_info = call_state.get_call_state(call_sid)
    if not call_info:
        response.say("I'm sorry, there was an error with your call.")
        response.hangup()
        return Response(str(response), mimetype='text/xml')

    goodbye_phrases = ['bye', 'goodbye', 'good bye', 'end call', 'hang up', 'thanks bye']
    if any(phrase in speech_result.lower() for phrase in goodbye_phrases):
        response.say("Thank you for your time. Goodbye!", voice='alice')
        response.hangup()
        call_state.end_call(call_sid)
        return Response(str(response), mimetype='text/xml')

    call_info['turn_count'] += 1
    if call_info['turn_count'] >= call_info['max_turns']:
        response.say("We've reached the maximum conversation time. Thank you for your time. Goodbye!", voice='alice')
        response.hangup()
        call_state.end_call(call_sid)
        return Response(str(response), mimetype='text/xml')

    if not speech_result:
        response.say("I didn't catch that. Could you please repeat?", voice='alice')
        gather = response.gather(
            input='speech',
            timeout=10,
            speech_timeout='auto',
            action=f'{NGROK_URL}/voice/process',
            method='POST'
        )
        return Response(str(response), mimetype='text/xml')
    
    try:
        customer_phone = call_info['customer_phone']
        ai_response = call_state.advisor_system.continue_conversation(customer_phone, speech_result)
        
        print(f"🤖 AI Response: {ai_response}")

        response.say(ai_response, voice='alice', language='en-US')
        
        state = call_state.advisor_system.conversation_states.get(customer_phone)
        if state and (state.conversation_complete or state.escalation_needed):
            response.say("Thank you for your time. Have a great day!", voice='alice')
            response.hangup()
            call_state.end_call(call_sid)
            return Response(str(response), mimetype='text/xml')

        gather = response.gather(
            input='speech',
            timeout=10,
            speech_timeout='auto',
            action=f'{NGROK_URL}/voice/process',
            method='POST'
        )

        response.say("Are you still there?", voice='alice')
        response.redirect(f'{NGROK_URL}/voice/process')
        
    except Exception as e:
        print(f"❌ Error processing speech: {str(e)}")
        response.say("I'm sorry, I had trouble processing your response. Could you please try again?")
        gather = response.gather(
            input='speech',
            timeout=10,
            speech_timeout='auto',
            action=f'{NGROK_URL}/voice/process',
            method='POST'
        )
    
    return Response(str(response), mimetype='text/xml')

@app.route('/voice/status', methods=['POST'])
def voice_status():
    """Handle call status updates"""
    call_sid = request.form.get('CallSid')
    call_status = request.form.get('CallStatus')
    
    print(f"📊 Call Status Update - SID: {call_sid}, Status: {call_status}")
    
    if call_status in ['completed', 'busy', 'no-answer', 'failed', 'canceled']:
        call_state.end_call(call_sid)
        print(f"🔚 Call {call_sid} ended with status: {call_status}")
    
    return Response('OK', mimetype='text/plain')

def get_customer_phone() -> Optional[str]:
    """Get customer phone number from user input."""
    while True:
        print("\nOptions:")
        print("1. Make an outbound call to a customer")
        print("9. Exit")
        
        choice = input("\nSelect an option (1 or 9): ").strip()
        
        if choice == "1":
            phone = input("Enter customer phone number (e.g., +1234567890): ").strip()
            if phone in CUSTOMER_DB:
                return phone
            else:
                print(f"❌ Customer not found for phone number: {phone}")
            
        elif choice == "9":
            print("👋 Goodbye!")
            return None
            
        else:
            print("❌ Invalid option. Please select 1 or 9.")

def start_flask_server():
    """Start the Flask server in a separate thread"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def main():
    """Main application entry point."""
    print("🎙️  Welcome to the Twilio Voice AI Loan Advisor System!")

    
    # Validate Twilio configuration
    if TWILIO_ACCOUNT_SID == 'your_account_sid_here' or TWILIO_AUTH_TOKEN == 'your_auth_token_here':
        print("Please configure your Twilio credentials in the environment variables or update the code directly.")
        print("TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, NGROK_URL")
        return
    
    if NGROK_URL == 'https://your-ngrok-url.ngrok.io':
        print("Please configure your ngrok URL in the NGROK_URL variable.")
        return
    
    try:
        print("Starting webhook server...")
        flask_thread = threading.Thread(target=start_flask_server, daemon=True)
        flask_thread.start()
        
        time.sleep(2)
        print("Webhook server started on http://localhost:5000")
        print(f" Webhook endpoints available at: {NGROK_URL}")
        print("\n Make sure your ngrok is running and pointing to localhost:5000")
        print("  Command: ngrok http 5000")
        
        while True:
            customer_phone = get_customer_phone()
            
            if customer_phone is None:
                break
            
            try:
                customer = CUSTOMER_DB[customer_phone]
                print(f"\n📞 Initiating outbound call to {customer.full_name} ({customer_phone})")
                
                if make_outbound_call(customer_phone):
                    print("✅ Call initiated successfully!")
                    print("🎙️  The AI agent will start the conversation when the call is answered.")
                    print("📱 You can monitor the call status in the console.")
                else:
                    print("❌ Failed to initiate call.")
                
                # Ask if user wants to make another call
                print("\n" + "="*50)
                another = input("Would you like to make another call? (y/n): ").strip().lower()
                if another not in ['y', 'yes']:
                    break
                    
            except KeyboardInterrupt:
                print("\n\n🛑 Application interrupted by user.")
                break
            except Exception as e:
                print(f"\n❌ An unexpected error occurred: {str(e)}")
                print("🔄 Returning to main menu...")
                continue
    
    except Exception as e:
        print(f"❌ FATAL ERROR: Failed to initialize system: {str(e)}")
        print("Please check your configuration and try again.")
        return
    
    print("\n👋 Thank you for using the Twilio Voice AI Loan Advisor System!")
    print("🏢 ABC Financial Services - Serving you better with AI")

if __name__ == "__main__":
    main()