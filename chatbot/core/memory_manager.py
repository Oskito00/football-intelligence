"""
Memory Manager - Handles conversation memory

Manages conversation history and context in memory (dict-based, no persistence for now).
"""

from datetime import datetime
from typing import Dict, Any, List

class MemoryManager:
    """Manages conversation memory and context."""
    
    def __init__(self):
        """Initialize the memory manager."""
        pass
    
    def add_message(self, role: str, content: str, conversation_memory: Dict[str, Any]) -> None:
        """
        Add a message to conversation memory.
        
        Args:
            role: Either 'user' or 'assistant'
            content: The message content
            conversation_memory: The conversation memory dict to update
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        conversation_memory["messages"].append(message)
        
        # Keep only last 50 messages to prevent memory from growing too large
        if len(conversation_memory["messages"]) > 50:
            conversation_memory["messages"] = conversation_memory["messages"][-50:]
    
    def get_recent_messages(self, conversation_memory: Dict[str, Any], count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent messages from conversation memory.
        
        Args:
            conversation_memory: The conversation memory dict
            count: Number of recent messages to return
            
        Returns:
            List of recent messages
        """
        messages = conversation_memory.get("messages", [])
        return messages[-count:] if messages else []
    
    def update_context(self, key: str, value: Any, conversation_memory: Dict[str, Any]) -> None:
        """
        Update context information in memory.
        
        Args:
            key: Context key
            value: Context value
            conversation_memory: The conversation memory dict to update
        """
        conversation_memory["context"][key] = value
    
    def get_context(self, key: str, conversation_memory: Dict[str, Any], default: Any = None) -> Any:
        """
        Get context value from memory.
        
        Args:
            key: Context key
            conversation_memory: The conversation memory dict
            default: Default value if key not found
            
        Returns:
            Context value or default
        """
        return conversation_memory.get("context", {}).get(key, default)
    
    def clear_context(self, conversation_memory: Dict[str, Any]) -> None:
        """
        Clear all context from memory.
        
        Args:
            conversation_memory: The conversation memory dict to update
        """
        conversation_memory["context"] = {}
    
    def get_memory_summary(self, conversation_memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a summary of the current memory state.
        
        Args:
            conversation_memory: The conversation memory dict
            
        Returns:
            Memory summary
        """
        messages = conversation_memory.get("messages", [])
        context = conversation_memory.get("context", {})
        
        return {
            "total_messages": len(messages),
            "user_messages": len([m for m in messages if m["role"] == "user"]),
            "assistant_messages": len([m for m in messages if m["role"] == "assistant"]),
            "context_keys": list(context.keys()),
            "session_started": conversation_memory.get("session_started"),
            "last_message_time": messages[-1]["timestamp"] if messages else None
        } 