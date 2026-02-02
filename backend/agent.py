from llama_cpp import Llama
import os
import json
import re
from backend.mcp_server import read_transactions, summarize_spending, generate_spending_chart

# Tool Definitions for Llama (OpenAI Compatible)
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_transactions",
            "description": "Search for transactions in the credit card statement based on filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "category": {"type": "string", "description": "Filter by category or merchant name"},
                    "min_amount": {"type": "number", "description": "Minimum transaction amount"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_spending",
            "description": "Get a summary of spending grouped by 'category' or 'month'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_by": {"type": "string", "enum": ["category", "month"], "default": "category"}
                },
                "required": ["group_by"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_spending_chart",
            "description": "Generate a visual chart (bar or pie) of spending.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_by": {"type": "string", "enum": ["category", "month"], "default": "category"},
                    "chart_type": {"type": "string", "enum": ["bar", "pie"], "default": "bar"}
                },
                "required": ["group_by"]
            }
        }
    }
]

class LocalAgent:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "Llama-3.2-3B-Instruct-Q4_K_M.gguf")
        self.llm = None
        self.messages = []
        
    def load_model(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}. Please run download_model.py")
            
        print("Loading Model... (this may take a moment)")
        # n_gpu_layers=0 for CPU only, increase if you have a GPU
        # n_ctx=2048 context window
        self.llm = Llama(
            model_path=self.model_path,
            n_gpu_layers=0, 
            n_ctx=4096,
            verbose=False
        )
        print("Model Loaded.")

    def chat(self, user_query: str):
        if not self.llm:
            self.load_model()
            
        # Hardcode current date so the AI doesn't search in 2022
        today = "2026-02-01"
        
        # Initialize System Prompt if empty
        if not self.messages:
            self.messages = [
                {"role": "system", "content": f"You are a Credit Card Analysis Assistant. Today's date is {today}.\n"
                                              "Available Tools:\n"
                                              "- read_transactions(start_date, end_date, category, min_amount)\n"
                                              "- summarize_spending(group_by='category'|'month')\n"
                                              "- generate_spending_chart(group_by='category'|'month', chart_type='bar'|'pie')\n\n"
                                              "RULES:\n"
                                              "1. If you need data, output ONLY a JSON call: {\"name\": \"tool_name\", \"parameters\": {...}}\n"
                                              "2. DO NOT EXPLAIN. DO NOT talk to yourself. Output ONLY the JSON if you need to call a tool.\n"
                                              "3. Once you have the data, provide a human-friendly answer.\n"
                                              "4. Never show technical JSON to the user.\n"
                                              "5. For general queries (e.g. 'spending'), default start_date to '2025-01-01' to filter effectively.\n"
                                              "6. ALWAYS use the Indian Rupee symbol (₹) for currency values.\n"
                                              "7. If user asks for 'items', 'transactions', or 'merchant' (e.g. 'Amazon', 'Uber', 'Food'), use read_transactions(category='Keyword')."}
            ]
        
        # Append User Query
        self.messages.append({"role": "user", "content": user_query})
        
        # Track executed tools and debug logs
        executed_tools = set()
        debug_logs = []
        debug_logs.append({
            "step": 0,
            "type": "system",
            "content": f"Received Query: {user_query}",
            "details": f"Context Date: {today}"
        })
        
        # Optimize Context: Keep only the system prompt + last 4 turns (8 messages)
        # We always keep the first message (System Prompt)
        if len(self.messages) > 9:
            # Keep system prompt (index 0) + last 8 messages
            self.messages = [self.messages[0]] + self.messages[-8:]
            print(f"⚠️ Context optimized: Kept last 8 messages. Current len: {len(self.messages)}")
        
        for i in range(5):
            response = self.llm.create_chat_completion(
                messages=self.messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto"
            )
            
            choice = response["choices"][0]
            message = choice["message"]
            content = (message.get("content") or "").strip()
            
            # 1. Native Tool Calls
            tool_calls = []
            if "tool_calls" in message:
                tool_calls = message["tool_calls"]
            
            # 2. Extract JSON from message content (fallback for stubborn models)
            if not tool_calls and content:
                # Find the FIRST { and LAST } - more robust than regex for nested JSON
                if '"name"' in content and '{' in content and '}' in content:
                    start_idx = content.find('{')
                    end_idx = content.rfind('}') + 1
                    json_str = content[start_idx:end_idx]
                    try:
                        loaded = json.loads(json_str)
                        if "name" in loaded:
                            args = loaded.get("parameters") or loaded.get("arguments") or {}
                            tool_calls = [{
                                "id": f"call_manual_{i}",
                                "function": {
                                    "name": loaded["name"],
                                    "arguments": json.dumps(args) if isinstance(args, dict) else str(args)
                                }
                            }]
                            # Important: Replace content in the actual message dictionary
                            message["content"] = "" 
                    except Exception:
                        pass
                
                # 3. Nudge if the model is talking about tools but didn't output valid JSON
                elif any(tool["function"]["name"] in content for tool in TOOLS_SCHEMA):
                    self.messages.append(message)
                    self.messages.append({"role": "system", "content": "ERROR: You mentioned a tool but did not output a valid JSON call. Please output ONLY the JSON for the tool call now."})
                    continue

            if not tool_calls:
                # If we've reached a final human answer, return it.
                if content:
                    # check if we have any pending chart images from this session to append
                    for msg in self.messages:
                        if msg.get("role") == "tool" and "![" in str(msg.get("content")):
                            tool_img = str(msg.get("content"))
                            if tool_img not in content:
                                content += f"\n\n{tool_img}"
                    
                    debug_logs.append({
                        "step": i + 1,
                        "type": "success",
                        "content": "Final Response Generated",
                        "details": ""
                    })
                    return content, debug_logs
                    
                elif i > 0: # We cleared a manual tool call, loop should have continued
                    pass
                else:
                    return "I'm ready to help. Please upload a statement or ask a question.", debug_logs

            # Execute Tools
            self.messages.append(message)
            
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                args_str = tool_call["function"]["arguments"]
                
                # Log the Tool Call
                debug_logs.append({
                    "step": i + 1,
                    "type": "tool_call",
                    "content": f"Calling: {func_name}",
                    "details": args_str
                })
                print(f"🛠️ Agent Calls Tool: {func_name}({args_str})")
                
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = {}
                
                # Sanitize
                valid_keys = ["start_date", "end_date", "category", "min_amount", "group_by", "chart_type"]
                filtered_args = {k: v for k, v in args.items() if k in valid_keys}
                
                # Create a signature for deduplication
                call_sig = f"{func_name}:{json.dumps(filtered_args, sort_keys=True)}"
                
                if call_sig in executed_tools:
                    print(f"[Turn {i}] Skipping duplicate call: {func_name}")
                    result = "Error: Tool already called with these arguments in this session. Do not call it again."
                    debug_logs.append({
                        "step": i + 1,
                        "type": "warning",
                        "content": "Skipping Duplicate Call",
                        "details": f"Already called: {func_name}"
                    })
                else:
                    executed_tools.add(call_sig)
                    print(f"[Turn {i}] Executing: {func_name} with {filtered_args}")
                    
                    try:
                        if func_name == "read_transactions":
                            result = read_transactions(**filtered_args)
                        elif func_name == "summarize_spending":
                            result = summarize_spending(**filtered_args)
                        elif func_name == "generate_spending_chart":
                            result = generate_spending_chart(**filtered_args)
                        else:
                            result = f"Error: Tool {func_name} not found"
                    except Exception as e:
                        result = f"Error: {str(e)}"
                
                # Log result preview
                str_result = str(result)
                print(f"  -> Result Length: {len(str_result)} chars")
                
                # Truncate for Debug Logs (keep slightly more detail)
                debug_detail = str_result[:2000] + "... (truncated)" if len(str_result) > 2000 else str_result
                debug_logs.append({
                    "step": i + 1,
                    "type": "tool_result",
                    "content": f"Result from {func_name}",
                    "details": debug_detail
                })
                    
                # AGGRESSIVE TRUNCATION for LLM Context
                # If result is huge, the LLM will choke. We must limit it.
                # 1000 chars is roughly 250-300 tokens. Safe.
                context_result = str_result
                if len(context_result) > 1200:
                    context_result = context_result[:1200] + f"\n... (Output truncated. {len(str_result) - 1200} characters omitted. Please refine your search.)"

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", "call_1"),
                    "name": func_name,
                    "content": context_result
                })
        
        return "I've reached the maximum analysis steps. Try asking about a specific category.", debug_logs

# Global Instance
agent_instance = LocalAgent()
