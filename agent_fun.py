# # agent_fun.py
# import asyncio
# import json
# import sys
# import re
# from typing import Dict, Any, List
# from contextlib import AsyncExitStack

# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client
# from ollama import chat

# # ---------------- HELPERS ----------------

# def extract_json(text: str) -> Dict[str, Any]:
#     """Extract first JSON object from text."""
#     # Clean markdown if present
#     text = re.sub(r"```json\s*", "", text)
#     text = re.sub(r"```\s*", "", text)
    
#     start_idx = text.find("{")
#     if start_idx == -1:
#         # If no brackets, the model failed completely
#         raise ValueError(f"No JSON brackets found in output: {text[:50]}...")
    
#     try:
#         decoder = json.JSONDecoder()
#         obj, _ = decoder.raw_decode(text[start_idx:])
#         return obj
#     except json.JSONDecodeError:
#         # Fallback: try standard loads if raw_decode is fussy about whitespace
#         try:
#             return json.loads(text[start_idx:])
#         except:
#             raise ValueError("Malformed JSON")

# def contains_tool_json(text: str) -> bool:
#     """Detects tool calls inside final answer"""
#     return '"action"' in text and '"args"' in text

# def format_tools_for_prompt(tools: List[Any]) -> str:
#     """Creates a clean schema for the LLM"""
#     desc = []
#     for t in tools:
#         # Simplify schema for 7B models
#         schema = {
#             "name": t.name,
#             "description": t.description,
#             "parameters": t.inputSchema
#         }
#         desc.append(json.dumps(schema))
#     return "\n".join(desc)

# def llm_json(messages: List[Dict[str, str]]) -> Dict[str, Any]:
#     """
#     LLM call with native JSON mode enabled.
#     This forces Ollama to output valid JSON.
#     """
#     try:
#         resp = chat(
#             model="mistral:7b",
#             messages=messages,
#             format="json",  # <--- MAGIC SWITCH: Forces strict JSON output
#             options={"temperature": 0} # 0 Temp = Maximum Determinism
#         )

#         raw = resp["message"]["content"]
#         return extract_json(raw)

#     except Exception as e:
#         print(f"⚠️ LLM Error: {e}. Retrying without JSON mode...")
#         # Fallback retry
#         resp = chat(
#             model="mistral:7b",
#             messages=messages + [{"role": "system", "content": "Respond using JSON ONLY."}],
#             options={"temperature": 0}
#         )
#         return extract_json(resp["message"]["content"])


# # ---------------- MAIN AGENT LOOP ----------------

# async def main():
#     # 1. Setup Server Path
#     server_path = sys.argv[1] if len(sys.argv) > 1 else "server_fun.py"

#     # 2. Connect to MCP Server
#     exit_stack = AsyncExitStack()
#     try:
#         stdio = await exit_stack.enter_async_context(
#             stdio_client(
#                 StdioServerParameters(
#                     command=sys.executable,
#                     args=[server_path]
#                 )
#             )
#         )
#         r_in, w_out = stdio
#         session = await exit_stack.enter_async_context(ClientSession(r_in, w_out))
#         await session.initialize()

#         # 3. Get Tools
#         tools = (await session.list_tools()).tools
#         tool_index = {t.name: t for t in tools}
#         print(f"🔌 Connected tools: {list(tool_index.keys())}")

#         # 4. Build System Prompt
#         tool_desc = format_tools_for_prompt(tools)
        
#         SYSTEM_PROMPT = f"""You are a precise JSON-RPC machine. You do NOT speak English. You ONLY output JSON.

# AVAILABLE TOOLS:
# {tool_desc}

# INSTRUCTIONS:
# 1. To call a tool, output this JSON structure:
# {{
#   "action": "tool_name",
#   "args": {{ "param": "value" }}
# }}

# 2. To answer the user (Final Answer), output this JSON structure:
# {{
#   "action": "final",
#   "answer": "Your answer here"
# }}

# IMPORTANT:
# - Output ONLY the JSON object. 
# - Do not add explanations.
# - Do not wrap in markdown.
# """

#         history = [{"role": "system", "content": SYSTEM_PROMPT}]

#         # 5. Chat Loop
#         while True:
#             try:
#                 user = input("\nYou: ").strip()
#                 if not user or user.lower() in {"exit", "quit"}:
#                     break
                
#                 # Reset history for specific task context to keep it clean (optional strategy)
#                 # For this simple agent, we append.
#                 history.append({"role": "user", "content": user})

#                 print("... thinking ...")

#                 for _ in range(8):  # Max 8 steps
#                     decision = llm_json(history)

#                     # --- CASE 1: FINAL ANSWER ---
#                     if decision.get("action") == "final":
#                         answer = str(decision.get("answer", ""))
#                         print(f"\n🤖 Agent: {answer}")
#                         history.append({"role": "assistant", "content": json.dumps(decision)})
#                         break

#                     # --- CASE 2: TOOL CALL ---
#                     tool_name = decision.get("action")
#                     args = decision.get("args", {})

#                     if tool_name not in tool_index:
#                         print(f"⚠️ Agent tried unknown tool: {tool_name}")
#                         history.append({"role": "system", "content": f"Error: Tool '{tool_name}' not found."})
#                         continue

#                     print(f"🛠  Calling: {tool_name}({args})")

#                     try:
#                         result = await session.call_tool(tool_name, args)
                        
#                         # Handle text vs complex content
#                         if result.content and hasattr(result.content[0], 'text'):
#                             tool_out = result.content[0].text
#                         else:
#                             tool_out = str(result)

#                         # Clean up tool output length for prompt context
#                         if len(tool_out) > 1000:
#                             tool_out = tool_out[:1000] + "... (truncated)"

#                         history.append({
#                             "role": "assistant", 
#                             "content": json.dumps(decision) # Add the call
#                         })
#                         history.append({
#                             "role": "tool", 
#                             "content": f"Tool Output: {tool_out}" # Add the result
#                         })
                        
#                     except Exception as e:
#                         print(f"❌ Tool Error: {e}")
#                         history.append({"role": "system", "content": f"Tool execution error: {e}"})

#             except KeyboardInterrupt:
#                 print("\n🛑 Interrupted by user.")
#                 break
#             except Exception as e:
#                 print(f"\n❌ Error in loop: {e}")
#                 break

#     finally:
#         await exit_stack.aclose()

# if __name__ == "__main__":
#     asyncio.run(main())


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
    "Decide step-by-step (ReAct). If you need a tool, output ONLY JSON:\n"
    '{"action":"tool_name","args":{...}}\n'
    "If you can answer, output ONLY JSON:\n"
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
 
            for _ in range(6):  # Increased safety loop for more complex reasoning
                decision = llm_json(history)
               
                # Debug: print decision
                print(f"\n[DEBUG] LLM decision: {decision}")
               
                if decision.get("action") == "final":
                    answer = decision.get("answer", "")
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
                    tool_response = f"[tool:{tname}] {payload}"
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