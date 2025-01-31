import requests

class TelegramBot:
    def __init__(self):
        self.token = "7756677801:AAGN72V1hYugCrSypWqE8WF-viYxfXm4dS0"
        self.chat_id = "7914809074"
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, message):
        """Send a message through Telegram"""
        endpoint = f"{self.base_url}/sendMessage"
        params = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"  # Allows for basic HTML formatting
        }
        
        try:
            response = requests.post(endpoint, params=params)
            if response.status_code == 200:
                print("Message sent successfully!")
            else:
                print(f"Failed to send message. Status code: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error sending message: {str(e)}")

# Example usage
if __name__ == "__main__":
    bot = TelegramBot()
    # Test message
    bot.send_message("""
<b>Test Message</b>
Hello! Your betting notification system is now set up! 🎲
    """)