#!/usr/bin/env python3
"""
Football Analytics Chatbot - Main Entry Point

A terminal-based natural language interface for football predictions and betting analytics.
"""

import sys
from pathlib import Path

from chatbot.core.chatbot import FootballChatbot
from chatbot.utils.helpers import print_banner, typewriter_print

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


def main():
    """Main entry point for the chatbot."""
    print_banner()
    
    # Initialize chatbot
    chatbot = FootballChatbot()
    
    print("🤖 Football Analytics Assistant ready!")
    print("💡 Try asking: 'What are your predictions for Tottenham vs Manchester United?'")
    print("Type 'quit', 'exit', or 'bye' to exit.\n")
    
    # Main conversation loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                print("\n👋 Thanks for using Football Analytics Assistant!")
                break
                
            if not user_input:
                continue
                
            # Process query and get response
            response = chatbot.process_query(user_input)
            
            # Print response with typewriter effect
            print("\n🤖 Assistant: ", end="")
            typewriter_print(response)
            print()  # Extra newline for spacing
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")

if __name__ == "__main__":
    main() 