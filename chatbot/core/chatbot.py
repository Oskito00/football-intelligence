"""
Main Chatbot Orchestrator

Coordinates LLM processing, function dispatch, and memory management.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional

from chatbot.core.llm_handler import LLMHandler
from chatbot.core.function_dispatcher import FunctionDispatcher
from chatbot.core.memory_manager import MemoryManager

class FootballChatbot:
    """Main chatbot class that orchestrates all components."""
    
    def __init__(self):
        """Initialize the chatbot with all components."""
        self.llm_handler = LLMHandler()
        self.function_dispatcher = FunctionDispatcher()
        self.memory_manager = MemoryManager()
        
        # Initialize conversation memory (dict, no persistence for now)
        self.conversation_memory = {
            "messages": [],
            "context": {},
            "session_started": datetime.now().isoformat()
        }
        
    def process_query(self, user_input: str) -> str:
        """
        Process a user query through the full pipeline.
        
        Args:
            user_input: Raw user question/command
            
        Returns:
            Natural language response
        """
        try:
            # Add user message to memory
            self.memory_manager.add_message("user", user_input, self.conversation_memory)
            
            # Parse query with LLM to extract intent and parameters
            parsed_query = self.llm_handler.parse_query(
                user_input, 
                self.conversation_memory
            )
            
            print(f"🔍 Parsed query: {parsed_query}")  # Debug output

            # Dispatch to appropriate function
            function_result = self.function_dispatcher.dispatch(parsed_query)
            
            print(f"📊 Function result: {function_result}")  # Debug output

            # For predictions and value bets use pre written response for others use the llm
            if parsed_query['intent'] in ['get_match_prediction', 'get_upcoming_value_bets', 'get_betting_recommendations', 'get_betting_value', 'get_upcoming_value_bets', 'get_upcoming_predictions', 'get_upcoming_matches', 'general_chat']:
                response = self.llm_handler.manual_response(
                    user_input,
                    parsed_query,
                    function_result,
                    self.conversation_memory
                )
            else:
                # Generate natural language response
                response = self.llm_handler.generate_response(
                user_input,
                parsed_query,
                function_result,
                self.conversation_memory
                )
            
            # Add assistant response to memory
            self.memory_manager.add_message("assistant", response, self.conversation_memory)
            
            return response
            
        except Exception as e:
            error_msg = f"I encountered an error processing your request: {str(e)}"
            self.memory_manager.add_message("assistant", error_msg, self.conversation_memory)
            return error_msg
    
    def reset_conversation(self):
        """Reset the conversation memory."""
        self.conversation_memory = {
            "messages": [], 
            "context": {},
            "session_started": datetime.now().isoformat()
        }
        
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get statistics about the current conversation."""
        messages = self.conversation_memory.get("messages", [])
        return {
            "total_messages": len(messages),
            "user_messages": len([m for m in messages if m["role"] == "user"]),
            "assistant_messages": len([m for m in messages if m["role"] == "assistant"]),
            "session_started": self.conversation_memory.get("session_started")
        } 