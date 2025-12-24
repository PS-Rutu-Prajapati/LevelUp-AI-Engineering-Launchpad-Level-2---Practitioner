# LevelUp: AI Engineering Launchpad - Level 2 (Practitioner)

An AI-powered assistant project that demonstrates the use of the Model Context Protocol (MCP) with AI language models. This project showcases how to build intelligent agents that can use tools to interact with external APIs and services.

## 📋 Overview

This project implements a **weekend helper AI assistant** that:
- Uses the **Groq API** with model identifiers `llama-3.1-8b-instant` (main reasoning) and `llama-3.3-70b-versatile` (reflection checks)
- Implements the **Model Context Protocol (MCP)** for tool integration
- Provides tools for weather information, book recommendations, and jokes
- Demonstrates ReAct (Reasoning + Acting) decision-making pattern

## 🎯 Project Structure

```
.
├── agent_fun.py          # MCP client that calls Groq API
├── server_fun.py         # MCP server with utility tools
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Key Components

**`agent_fun.py`** - The AI Agent Client
- Connects to the Groq API using model `llama-3.1-8b-instant` for main reasoning and `llama-3.3-70b-versatile` for reflection checks
- Implements a ReAct pattern for step-by-step reasoning
- Manages MCP client sessions for tool access
- Requires `GROQ_API_KEY` environment variable

**`server_fun.py`** - The MCP Server with Tools
- **`get_weather()`** - Fetches current weather data via Open-Meteo API
- **`book_recs()`** - Suggests books based on topics via Open Library API
- **`random_joke()`** - Returns a clean, single-line joke via JokeAPI

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- A Groq API key (get one at [console.groq.com](https://console.groq.com))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/PS-Rutu-Prajapati/LevelUp-AI-Engineering-Launchpad-Level-2.git
   cd LevelUp\ 2
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

### Running the Project

```bash
python agent_fun.py
```

The agent will start and be ready to help with queries about:
- Current weather conditions at specific locations
- Book recommendations on various topics
- Funny jokes

## 📦 Dependencies

Key packages used in this project:

| Package | Purpose |
|---------|---------|
| `mcp` | Model Context Protocol implementation |
| `groq` / `requests` | API communication |
| `python-dotenv` | Environment variable management |
| `httpx` | Async HTTP client |
| `jsonschema` | JSON validation |
| `ollama` | Integration with Ollama models (optional) |

See [requirements.txt](requirements.txt) for the complete list.

## 🔧 How It Works

1. **User Query** → Agent receives a question
2. **Reasoning** → Agent decides if it needs to use tools
3. **Tool Execution** → MCP client calls available tools (weather, books, jokes)
4. **Response** → Agent formulates a helpful answer
5. **Output** → Returns JSON response to the user

## Try these prompts

1. Plan a cozy Saturday in New York at (40.7128, -74.0060). Include the current weather, 2 book ideas about mystery, one joke, and a dog pic.
2. What’s the temperature now at (37.7749, -122.4194)? Keep it brief.
3. Give me one trivia question.
