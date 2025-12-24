import asyncio
import json
import sys
import os
from typing import Dict, Any, List
from contextlib import AsyncExitStack
import requests  # Added for Groq API calls
from dotenv import load_dotenv  # Added for .env support
 
# Load environment variables from .env file
load_dotenv()
 
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
 
# Get Groq API key from environment variable
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file or environment variables")
 
SYSTEM = (
    "You are a helpful assistant with access to tools.\n"
    "When using a tool, output ONLY JSON:\n"
    '{"action":"<tool_name>","args":{...}}\n\n'
    "Available tools:\n"
    "- get_weather(latitude: float, longitude: float)\n"
    "- city_to_coords(city: str)\n"
    "- book_recs(topic: str, limit: int)\n"
    "- random_joke()\n"
    "- random_dog()\n"
    "- trivia()\n\n"
    "For weather questions, ALWAYS use get_weather.\n"
    "When answering finally, output ONLY:\n"
    '{"action":"final","answer":"..."}'
)


 
def llm_json(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Call Groq API with Llama 3.3 70B model"""
   
    # Prepare the payload for Groq API
    groq_messages = []
    for msg in messages:
        # Convert to Groq message format
        groq_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
   
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": groq_messages,
        "temperature": 0.2,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"}  # Force JSON output
    }
   
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
   
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
       
        result = response.json()
        content = result["choices"][0]["message"]["content"]
       
        # Try to parse JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback: return as final answer
                return {"action": "final", "answer": content}
               
    except requests.exceptions.RequestException as e:
        print(f"Groq API error: {e}")
        return {"action": "final", "answer": f"API error: {str(e)}"}
 
def reflect_with_groq(answer: str) -> str:
    """Use Groq for reflection check"""
    reflection_prompt = (
        "Check if the following response is correct, complete, and has no obvious mistakes. "
        "If it's fine, reply with exactly 'looks good'. "
        "If there are issues, provide the corrected answer."
    )
   
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": reflection_prompt},
            {"role": "user", "content": answer}
        ],
        "temperature": 0,
        "max_tokens": 256
    }
   
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
   
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except:
        return "looks good"  # Fallback if reflection fails
 
async def main():
    server_path = sys.argv[1] if len(sys.argv) > 1 else "server_fun.py"
    exit_stack = AsyncExitStack()
    stdio = await exit_stack.enter_async_context(
        stdio_client(StdioServerParameters(command="python", args=[server_path]))
    )
    r_in, w_out = stdio
    session = await exit_stack.enter_async_context(ClientSession(r_in, w_out))
    await session.initialize()
 
    tools = (await session.list_tools()).tools
    tool_index = {t.name: t for t in tools}
    print("Connected tools:", list(tool_index.keys()))
 
    history = [{"role": "system", "content": SYSTEM}]
    try:
        while True:
            user = input("\nYou: ").strip()
            if not user or user.lower() in {"exit", "quit", "q"}:
                break
            history.append({"role": "user", "content": user})
 
            for _ in range(3):  # Increased safety loop for more complex reasoning
                decision = llm_json(history)
               
                # Debug: print decision
                print(f"\n[DEBUG] LLM decision: {decision}")
               
                if decision.get("action") == "final":
                    answer = decision.get("answer", "")

                    # Prefer structured tool-derived answers when available
                    # Look back through history for recent tool outputs encoded as JSON
                    for h in reversed(history):
                        content = h.get("content")
                        if not isinstance(content, str):
                            continue
                        try:
                            obj = json.loads(content)
                        except Exception:
                            continue

                        if isinstance(obj, dict) and obj.get("tool") == "trivia":
                            res = obj.get("result")
                            # result might already be a dict or a JSON string
                            if isinstance(res, dict) and res.get("correct"):
                                answer = res.get("correct")
                                break
                            if isinstance(res, str):
                                try:
                                    parsed = json.loads(res)
                                    if isinstance(parsed, dict) and parsed.get("correct"):
                                        answer = parsed.get("correct")
                                        break
                                except Exception:
                                    pass

                        if isinstance(obj, dict) and obj.get("tool") == "get_weather":
                            res = obj.get("result")
                            if isinstance(res, dict):
                                # Prefer explicit temperature fields if present
                                if "temperature" in res:
                                    answer = f"The current temperature at ({res.get('latitude','?')}, {res.get('longitude','?')}) is {res['temperature']}"
                                    break
                                if "temperature_2m" in res:
                                    answer = f"The current temperature is {res['temperature_2m']} °C"
                                    break

                    # One-shot reflection
                    reflection_result = reflect_with_groq(answer)
                    if reflection_result.lower() != "looks good":
                        answer = reflection_result
                    print(f"\nAgent: {answer}")
                    history.append({"role": "assistant", "content": answer})
                    break
 
                tname = decision.get("action")
                args = decision.get("args", {})
               
                if not tname:
                    history.append({"role": "assistant", "content": f"(no action specified in {decision})"})
                    continue
                   
                if tname not in tool_index:
                    history.append({"role": "assistant", "content": f"(unknown tool '{tname}'. Available: {list(tool_index.keys())})"})
                    continue
 
                try:
                    result = await session.call_tool(tname, args)
                    payload = result.content[0].text if result.content else json.dumps(result.model_dump())
                    tool_response = json.dumps({
    "tool": tname,
    "result": result.content[0].text if result.content else result.model_dump()
})

                    print(f"\n[Tool called: {tname}]")
                    history.append({"role": "assistant", "content": tool_response})
                except Exception as e:
                    error_msg = f"[tool error:{tname}] {str(e)}"
                    history.append({"role": "assistant", "content": error_msg})
                    print(f"\n{error_msg}")
                   
    finally:
        await exit_stack.aclose()
 
if __name__ == "__main__":
    asyncio.run(main())