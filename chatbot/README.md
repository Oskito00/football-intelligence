# Football Analytics Chatbot

A terminal-based natural language interface for football predictions and betting analytics.

## Overview

This chatbot serves as an intelligent assistant for football analytics, allowing users to ask questions in natural language and get AI-powered insights about match predictions, betting value, and analytics.

## Architecture

```
chatbot/
├── main.py                     # Entry point
├── core/                       # Core chatbot components
│   ├── chatbot.py             # Main orchestrator
│   ├── llm_handler.py         # Query parsing & response generation
│   ├── function_dispatcher.py # Routes to analytics functions
│   └── memory_manager.py      # Conversation memory
├── functions/                  # Analytics functions
│   ├── match_predictions.py   # Get predictions by match_id
│   └── match_finder.py        # Find matches by team names
└── utils/                     # Utility functions
    └── helpers.py             # Helper functions
```

## Features

### Current Capabilities
- **Match Predictions**: Get predictions for specific team matchups
  - Example: "What are your predictions for Tottenham vs Manchester United?"
  
- **Fuzzy Team Matching**: Intelligent team name recognition
  - Handles variations like "Man United", "Man City", "Spurs", etc.
  
- **Conversation Memory**: Maintains context during conversation (in-memory only)

### Coming Soon
- Betting value analysis
- Bet sizing recommendations  
- Odds comparison
- Team form analysis

## Usage

### Quick Start

```bash
# Run the chatbot
python chatbot/main.py
```

### Example Conversations

```
You: What are your predictions for Arsenal vs Chelsea?

🤖 Assistant: Based on my analysis, Arsenal is likely to beat Chelsea. 
My confidence in this prediction is 68.5%.

Detailed probabilities:
• Arsenal win: 68.5%
• Draw: 18.2%
• Chelsea win: 13.3%
```

## Architecture Details

### Core Components

#### 1. Chatbot Orchestrator (`chatbot.py`)
- Coordinates all components
- Manages conversation flow
- Handles error cases

#### 2. LLM Handler (`llm_handler.py`)  
- Parses user queries to extract intent and parameters
- Generates natural language responses
- Currently uses rule-based parsing (ready for LLM integration)

#### 3. Function Dispatcher (`function_dispatcher.py`)
- Maps intents to specific analytics functions
- Handles function execution and error management
- Easily extensible for new analytics functions

#### 4. Memory Manager (`memory_manager.py`)
- Manages conversation history
- Stores context information
- Currently in-memory only (no persistence)

### Analytics Functions

#### Match Finder (`match_finder.py`)
- Fuzzy search for matches by team names
- Handles team name variations and abbreviations
- Connects to your existing database or provides mock data

#### Match Predictions (`match_predictions.py`)
- Retrieves predictions by match_id
- Integrates with your ML pipeline predictions
- Provides mock data for testing

## Configuration

### Database Integration
The chatbot integrates with your existing database structure:
- Uses your `config.py` for database connection
- Queries `matches` table for match data
- Queries `match_result_predictions` table for predictions

### Adding New Functions

1. **Create the function** in `chatbot/functions/`
2. **Add intent handling** in `llm_handler.py`
3. **Register the function** in `function_dispatcher.py`

Example:
```python
# In function_dispatcher.py
def _handle_betting_analysis(self, parsed_query):
    from chatbot.functions.betting_analysis import analyze_betting_value
    return analyze_betting_value(parsed_query["parameters"])
```

## Development

### Mock Data Mode
When database is unavailable, the system automatically falls back to mock data for testing.

### Debug Mode
Set debug flags in the main chatbot to see:
- Parsed query details
- Function execution results
- Response generation process

### Testing
```bash
# Test individual components
python -c "from chatbot.functions.match_finder import find_matches_by_teams; print(find_matches_by_teams('Arsenal', 'Chelsea'))"
```

## Extension Points

### Easy to Add:
- **New Analytics Functions**: Just add to `functions/` directory
- **New Intents**: Add patterns to `llm_handler.py`
- **LLM Integration**: Replace rule-based parsing with actual API calls
- **Persistence**: Add JSON/database persistence to memory manager
- **Web Interface**: The core can be wrapped with FastAPI/Flask

### Future Enhancements
- Real LLM integration (Claude/GPT APIs)
- Persistent conversation memory
- Web-based chat interface
- Voice interface
- Integration with live odds APIs
- Advanced analytics dashboards

## Dependencies

```python
# Core requirements
psycopg2-binary  # Database connection
python-dateutil  # Date parsing
```

## Contributing

The architecture is designed to be easily extensible:

1. **Add analytics functions** in `functions/`
2. **Extend LLM patterns** in `llm_handler.py`  
3. **Add utility functions** in `utils/`
4. **Test with mock data** before database integration

## License

Part of the InBETments project. 