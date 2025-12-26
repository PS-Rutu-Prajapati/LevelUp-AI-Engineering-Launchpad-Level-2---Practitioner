# LevelUp: AI Engineering Launchpad - Level 2 (Practitioner)

An AI-powered assistant project that demonstrates the use of the Model Context Protocol (MCP) with AI language models. This project showcases how to build intelligent agents that can use tools to interact with external APIs and services.

## 📋 Overview

This project implements a **weekend helper AI assistant** that:
- Uses the **Groq API** with `llama-3.3-70b-versatile` model for intelligent reasoning
- Implements the **Model Context Protocol (MCP)** for tool integration
- Provides 6 tools for weather, books, jokes, dogs, city coordinates, and trivia
- Intelligently decides which tools to call based on user queries
- Handles both single and multiple tool calls seamlessly

## 🎯 Project Structure

```
.
├── agent_fun.py          # MCP client that calls Groq API
├── server_fun.py         # MCP server with utility tools
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Key Components

- **`agent_fun.py`** - The AI Agent Client
  - Connects to Groq API using `llama-3.3-70b-versatile` model
  - Intelligently decides which tools to call (single or multiple)
  - Executes tools and synthesizes results into natural language responses

**`server_fun.py`** - The MCP Server with Tools
- **`get_weather(latitude, longitude)`** — Current weather data via Open-Meteo API (temperature, wind speed, weather code)
- **`book_recs(topic, limit=5)`** — Book suggestions from a topic via Open Library API
- **`random_joke()`** — Clean, safe single-line jokes via JokeAPI
- **`random_dog()`** — Random dog breed image URLs via Dog CEO API
- **`city_to_coords(city)`** — Resolve city names to geographic coordinates via Open-Meteo Geocoding API
- **`trivia()`** — Multiple-choice trivia questions via Open Trivia Database (unescapes HTML entities)

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

5. **Run the agent**
    ```bash
    python agent_fun.py
    ```

Usage notes
- At the prompt type natural queries. For example:
  - "What is the temperature at (37.7749, -122.4194)?"
  - "Give me one trivia question."
  - Plan a cozy Saturday in New York at (40.7128, -74.0060). Include the current weather, 2 book ideas about mystery, one joke, and a dog pic.
- The agent will decide whether to call a tool. Tool calls are logged as `[Tool called: <name>]` and the tool response is stored in the conversation history as JSON.