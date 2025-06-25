import aiohttp
import asyncio
import json
import httpx

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

# async def resolve_statement():
#     """
#     Call the resolve endpoint to get resolution for a statement.
    
#     Args:
#         statement: Statement to resolve.
        
#     Returns:
#         Resolution data from the API.
#     """
#     client = httpx.AsyncClient(timeout=timeout)
#     api_url = "https://degenbrain.com"
#     try:
#         # Build request payload
#         payload = {
#             "statement": "Will the New York Yankees win the 2024 World Series?",
#             "createdAt": "2025-06-22T18:21:48.302943+00:00",
#             "initialValue": None,
#             "direction": None,
#             "end_date": "2024-11-01T23:59:59Z"
#         }
        
#         print("Resolving statement via API " + payload['statement'] + f"{api_url}/resolve")
        
#         # Make API call
#         response = await client.post(
#             f"{api_url}/resolve",
#             json=payload
#         )
#         response.raise_for_status()
        
#         result = response.json()
#         print("result:\n" + result)
#         print("Statement resolved" + result.get("resolution") + result.get("confidence"))
        
#         return result
        
#     except httpx.HTTPStatusError as e:
#         print("API returned error status")
#         raise
#     except Exception as e:
#         print("Failed to resolve statement", error=str(e))
#         raise

def call_degenbrain_api():
    requests = httpx.Client(timeout=timeout)
    url = "https://degenbrain.com/api/resolve-job/start/"
    
    payload = {
        "statement": "ETH blockchain had over 800,000 active validators at the end of 2024.",
        "createdAt": "2025-05-26T18:14:00.000Z"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print("result:")
        print(result)
        return result
    except httpx.HTTPStatusError as e:
        print("1 API returned error status")
        raise
    except requests.exceptions.RequestException as e:
        print(f"Có lỗi khi gọi API: {e}")
        return None

def check_job_status(job_id):
    requests = httpx.Client(timeout=timeout)
    url = f"https://degenbrain.com/api/resolve-job/status/{job_id}/"
    
    try:
        response = requests.get(url)
        result = response.json()
        # print("result:")
        # print(result)
        return result
    except httpx.HTTPStatusError as e:
        print("2 API returned error status")
        raise
    except requests.exceptions.RequestException as e:
        print(f"Có lỗi khi kiểm tra status: {e}")
        return None

def process_job():
    # Bắt đầu job
    start_result = call_degenbrain_api()
    if not start_result:
        print("Không thể bắt đầu job")
        return
    
    # Lấy job_id từ response
    job_id = start_result.get('job_id')
    if not job_id:
        print("Không tìm thấy job ID trong response")
        return
    
    print(f"Job đã được tạo với ID: {job_id}")
    
    # Kiểm tra status
    import time
    while True:
        status_result = check_job_status(job_id)
        if status_result:
            print(f"Trạng thái job: {status_result}")
            if status_result['status'] != 'completed':
                time.sleep(1)
                continue
            else:
                break

        

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
    # asyncio.run(_call_openai(prompt=reasoning_prompt, response_format='json'))
    # asyncio.run(resolve_statement())
    process_job()

if __name__ == "__main__":
    main()