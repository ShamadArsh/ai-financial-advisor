import asyncio
import os
import sys
import json
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from groq import Groq

load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
alpaca_server_path = os.path.join(current_dir, "alpaca_server.py")

if not os.path.exists(alpaca_server_path):
    print(f"❌ ERROR: Cannot find {alpaca_server_path}")
    sys.exit(1)

alpaca_params = StdioServerParameters(
    command=sys.executable,
    args=[alpaca_server_path],
    env=os.environ.copy()
)


def mcp_tools_to_groq(mcp_tools):
    """Convert MCP tool definitions to Groq/OpenAI tool format."""
    tools = []
    for tool in mcp_tools:
        schema     = tool.inputSchema if hasattr(tool, 'inputSchema') else {}
        properties = schema.get("properties", {})
        required   = schema.get("required", [])

        # Groq requires at least an empty object for parameters
        parameters = {
            "type": "object",
            "properties": properties if properties else {},
        }
        if required:
            parameters["required"] = required

        tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": parameters,
            }
        })
    return tools


async def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ ERROR: GROQ_API_KEY not found in .env")
        return

    client = Groq(api_key=api_key)

    async with stdio_client(alpaca_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            alpaca_tools = (await session.list_tools()).tools
            groq_tools   = mcp_tools_to_groq(alpaca_tools)
            print(f"[*] Alpaca tools: {[t.name for t in alpaca_tools]}")

            # Verify tool schemas look correct
            for t in groq_tools:
                print(f"  - {t['function']['name']}: {list(t['function']['parameters']['properties'].keys())}")

            system_prompt = (
                "You are an AI paper trading assistant connected to Alpaca.\n"
                "You can place market orders, limit orders, check positions,\n"
                "view open orders, cancel orders, and check account balance.\n"
                "This is PAPER TRADING — no real money involved.\n"
                "Always confirm trade details before executing."
            )

            print("\n--- 🤖 AI TRADING AGENT (GROQ + ALPACA PAPER) ---")
            print("Try: 'Check my balance' / 'Buy 2 shares of NVDA' / 'Show positions'")
            print("Type 'exit' to quit.\n")

            chat_history = [{"role": "system", "content": system_prompt}]

            while True:
                user_input = input("You > ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                if not user_input:
                    continue

                try:
                    chat_history.append({"role": "user", "content": user_input})

                    while True:
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=chat_history,
                            tools=groq_tools,
                            tool_choice="auto",
                        )

                        message = response.choices[0].message

                        # Build assistant message cleanly
                        assistant_msg = {
                            "role": "assistant",
                            "content": message.content or "",
                        }
                        if message.tool_calls:
                            assistant_msg["tool_calls"] = [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments,
                                    }
                                }
                                for tc in message.tool_calls
                            ]
                        chat_history.append(assistant_msg)

                        # No tool calls — final answer
                        if not message.tool_calls:
                            print(f"\nAI > {message.content}\n")
                            break

                        # Execute each tool call
                        for tc in message.tool_calls:
                            fn_name = tc.function.name
                            try:
                                fn_args = json.loads(tc.function.arguments)
                            except Exception:
                                fn_args = {}

                            print(f"  [tool] {fn_name}({fn_args})")

                            try:
                                result      = await session.call_tool(fn_name, arguments=fn_args)
                                tool_output = result.content[0].text if result.content else "No result"
                            except Exception as e:
                                tool_output = f"Tool error: {e}"

                            print(f"  [result] {tool_output[:200]}")

                            chat_history.append({
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": tool_output,
                            })

                except Exception as e:
                    print(f"[!] Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())