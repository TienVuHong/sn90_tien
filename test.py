import aiohttp
import asyncio
import json

openai_api_key = 'sk-223e1212859d4cd0b4b83d3ee472bc6d'
timeout = 60

reasoning_prompt = f"""
You are a research and analysis expert. Based on the statement provided, search for sources on the internet, analyze and determine if this prediction statement is TRUE, FALSE, or PENDING.

Statement: Will the betting favorite win the 2024 Belmont Stakes?
End Date: 2024-06-08T23:59:59Z
Current Date: 2025-06-22T17:33:23.040947+00:00

Consider:
1. Has the deadline passed? If yes, search through the internet for evidence and determine the resolution. If not, search through the internet and predict the resolution
2. What is your confidence level (0-100)? For the event that happended, give high confidence.
3. What sources support your conclusion? Mention at least 3 different sources.
4. If statement is about crypto price prediction, prefer getting data through api and analyze information from "coingecko.com", "coinmarketcap.com", "bloomberg.com", "reuters.com", "coinbase.com", "kraken.com".

Respond in JSON format:
{{
    "resolution": "TRUE|FALSE",
    "confidence": 85,
    "summary": "Detailed explanation of your reasoning...",
    "sources": ["https://example.com/evidence", "https://api.coingecko.com/api/v3/simple/price"],
    "key_evidence": "What evidence supports this conclusion"
}}
"""

async def _call_openai(prompt: str, response_format: str = "text"):
    """Call OpenAI API for reasoning."""
    if not openai_api_key:
        print("OpenAI API key not provided, using fallback")
        return {
            "resolution": "PENDING",
            "confidence": 30,
            "summary": "OpenAI API key not configured",
            "sources": ["config_error"],
            "key_evidence": "No OpenAI API key available"
        }
    
    try:
        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a research and analysis expert. Analyze statements accurately and provide structured responses in the requested JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Low temperature for consistent responses
            "max_tokens": 1000
        }
        
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.post("https://api.deepseek.com/v1/chat/completions", 
                                    headers=headers, 
                                    json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    print(result)
                    if response_format == "json":
                        pass
                        # try:
                        #     ret = json.loads(content)
                        #     print(json.dumps(ret, indent=4))
                        #     return ret
                        # except json.JSONDecodeError:
                        #     print("Failed to parse OpenAI JSON response", content=content)
                        #     return {"error": "Invalid JSON response from OpenAI"}
                    else:
                        return content
                else:
                    error_text = await response.text()
                    print("OpenAI API error", status=response.status, error=error_text)
                    return {"error": f"OpenAI API error: {response.status}"}
                    
    except Exception as e:
        print("OpenAI API call failed", error=str(e))
        return {"error": f"OpenAI API call failed: {str(e)}"}
    
def main():
    asyncio.run(_call_openai(prompt=reasoning_prompt, response_format='json'))

if __name__ == "__main__":
    main()