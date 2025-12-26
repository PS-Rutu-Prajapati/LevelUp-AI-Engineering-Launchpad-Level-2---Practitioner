# agent_fun.py
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
    "You are a cheerful weekend helper. You can call MCP tools.\n"
    "Available tools: get_weather, book_recs, random_joke, random_dog, city_to_coords, trivia\n\n"
    "When you need a tool, output ONLY valid JSON with the real tool name and args:\n"
    '{"action":"get_weather","args":{"latitude":40.7128,"longitude":-74.0060}}\n'
    'or {"action":"book_recs","args":{"topic":"mystery","limit":2}}\n'
    'or {"action":"random_joke","args":{}}\n'
    'or {"action":"trivia","args":{"amount":1}}\n\n'
    "When you have gathered enough info and can answer, output ONLY JSON:\n"
    '{"action":"final","answer":"Your friendly answer summarizing what you found"}\n\n'
    "DO NOT output 'tool_name' or '...' or {...}. Always use REAL tool names and concrete args."
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
            original_query = user  # Store original query for context
 
            for loop_count in range(6):  # reasoning/tool loop
                decision = llm_json(history)
               
                # Debug: print decision
                print(f"\n[DEBUG] LLM decision: {decision}")
               
                # Handle both single dict and list of dicts
                if isinstance(decision, list):
                    # Multiple actions: execute each one
                    for action_obj in decision:
                        if not isinstance(action_obj, dict):
                            continue
                        if action_obj.get("action") == "final":
                            answer = action_obj.get("answer", "")
                            print(f"\nAgent: {answer}")
                            history.append({"role": "assistant", "content": answer})
                            break
                        
                        tname = action_obj.get("action")
                        args = action_obj.get("args", {})
                        
                        if not tname or tname not in tool_index:
                            print(f"[ERROR] Unknown tool '{tname}'")
                            continue
                        
                        try:
                            result = await session.call_tool(tname, args)
                            payload = result.content[0].text if result.content else json.dumps(result.model_dump())
                            print(f"[Tool called: {tname}]")
                            history.append({"role": "assistant", "content": f"[tool:{tname}] {payload}"})
                        except Exception as e:
                            print(f"[Tool error: {tname}] {str(e)}")
                            history.append({"role": "assistant", "content": f"[tool error:{tname}] {str(e)}"})
                    
                    # After executing all tools in the list, ask the LLM for a final answer
                    history.append({"role": "user", "content": f"Based on the tool results above, respond to the original query: '{original_query}'"})
                    final_decision = llm_json(history)
                    print(f"\n[DEBUG] Final LLM decision: {final_decision}")
                    if isinstance(final_decision, dict) and final_decision.get("action") == "final":
                        answer = final_decision.get("answer", "")
                        print(f"\nAgent: {answer}")
                        history.append({"role": "assistant", "content": answer})
                    else:
                        print(f"\nAgent: I've gathered all the information from the tools above for your cozy Saturday plan.")
                        history.append({"role": "assistant", "content": "I've gathered all the information from the tools above for your cozy Saturday plan."})
                    break
                
                # Single dict case
                if isinstance(decision, dict):
                    if decision.get("action") == "final":
                        answer = decision.get("answer", "")
                        print(f"\nAgent: {answer}")
                        history.append({"role": "assistant", "content": answer})
                        break

                    # Force final answer if we've looped too many times
                    if loop_count >= 5:
                        answer = "I've gathered information from the tools. Here's what I found from the tool calls above."
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
                        tool_response = f"[tool:{tname}] {payload}"
                        print(f"\n[Tool called: {tname}]")
                        history.append({"role": "assistant", "content": tool_response})
                    except Exception as e:
                        error_msg = f"[tool error:{tname}] {str(e)}"
                        history.append({"role": "assistant", "content": error_msg})
                        print(f"\n{error_msg}")
                    
                    # After single tool call, ask LLM for final answer
                    history.append({"role": "user", "content": f"Based on the tool result above, respond to the original query: '{original_query}'"})
                    final_decision = llm_json(history)
                    print(f"\n[DEBUG] Final LLM decision: {final_decision}")
                    if isinstance(final_decision, dict) and final_decision.get("action") == "final":
                        answer = final_decision.get("answer", "")
                        print(f"\nAgent: {answer}")
                        history.append({"role": "assistant", "content": answer})
                    else:
                        print(f"\nAgent: I've processed the tool result above.")
                        history.append({"role": "assistant", "content": "I've processed the tool result above."})
                    break
                   
    finally:
        await exit_stack.aclose()
 
if __name__ == "__main__":
    asyncio.run(main())