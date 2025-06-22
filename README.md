# Conversational AI Loan Advisor Agent

Automated voice agent for loan management that handles customer verification, EMI reminders, payment collection, and payment plans through outbound calls.

## Features
- **Customer Verification**: Automated identity verification
- **EMI Reminders**: Payment due notifications
- **Payment Collection**: Outstanding payment discussions
- **Payment Plans**: Flexible repayment options
- **Response Recording**: Tracks Paid/Promise to Pay/Dispute responses
- **Smart Escalation**: Automatically escalates complex cases

## Quick Setup

### 1. Environment Setup
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```
### 2. Start ngrok
```bash
ngrok.exe http 5000
````
Copy the public HTTPS URL (e.g., https://abc123.ngrok.io)
### 3. Configure Environment
Create .env file
```env
# Twilio Credentials
TWILIO_ACCOUNT_SID='your_account_sid'
TWILIO_AUTH_TOKEN='your_auth_token'
TWILIO_PHONE_NUMBER='+1234567890'
NGROK_URL='https://abc123.ngrok.io'

# OpenAI API
OPENAI_API_KEY='your_openai_api_key'
```
### 4. Run Application
```bash
python main.py
```
## Requirements
Python 3.7+

Twilio Account with phone number

OpenAI API key

ngrok for webhook tunneling
