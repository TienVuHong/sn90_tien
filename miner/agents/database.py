import sqlite3
import json

# conn = sqlite3.connect('sn90.db')
# cursor = conn.cursor()
# cursor.execute('''
#     CREATE TABLE IF NOT EXISTS Data_table (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         statement TEXT NOT None,
#         response TEXT NOT None
#     )
# ''')

def insert_data(statement, response_dict):
    conn = sqlite3.connect('sn90.db')
    cursor = conn.cursor()
    res = get_response(statement)
    if res is not None:
        # If the confidence is not better, do nothing
        if response_dict['confidence'] <= res['confidence']:
            conn.close()
            return
        
        response_json = json.dumps(response_dict)
        cursor.execute('''
            UPDATE Data_table SET response = ? WHERE statement = ?
        ''', (response_json, statement))
    else:
        response_json = json.dumps(response_dict)
        cursor.execute('''
            INSERT INTO Data_table (statement, response) VALUES (?, ?)
        ''', (statement, response_json))
    conn.commit()
    conn.close()

def get_response(statement):
    conn = sqlite3.connect('sn90.db')
    cursor = conn.cursor()
    cursor.execute('SELECT response FROM Data_table WHERE LOWER(statement) = LOWER(?)', (statement,))
    row = cursor.fetchone()
    conn.close()
    if row:
        response_json = row[0]
        return json.loads(response_json)
    else:
        return None
result = [
{"statement": "Will Bitcoin close above $90,000 by May 12, 2025?", "resolution": "PENDING", "confidence": 100, "summary": "The threshold crossing status is unknown, and the market close date has passed without confirmation of crossing. The prediction remains unresolved as PENDING.", "target_date": "2025-05-12T00:00:00Z", "target_value": 90000, "current_value": 107340, "direction_inferred": "above", "sources": ["CoinGecko", "coinmarketcap", "coinbase", "reuters", "binance", "coinbase", "kraken"]},
{"statement": "Will the New York Yankees win the 2024 World Series?", "resolution": "FALSE", "confidence": 100, "summary": "The New York Yankees did not win the 2024 World Series. The available data confirms that they have won 27 titles historically, but there is no indication of a 2024 victory. This makes the prediction false.", "target_date": "2024-10-01T00:00:00Z", "target_value": None, "current_value": None, "direction_inferred": None, "sources": ["Google Search", "coingecko", "coinmarketcap", "coinbase", "https://www.espn.com/mlb/story/_/id/39806597/who-won-most-world-series-titles-mlb-history", "https://en.wikipedia.org/wiki/List_of_World_Series_champions", "https://www.mlb.com/yankees/standings", "https://en.wikipedia.org/wiki/2024_World_Series", "https://www.reddit.com/r/mlb/comments/1g7q5mg/official_the_new_york_yankees_advance_to_the_2024/"]},
{"statement": "Will Joe Biden drop out of the 2024 presidential race before August 1, 2024?", "resolution": "TRUE", "confidence": 100, "summary": "Joe Biden announced his withdrawal from the 2024 United States presidential election on July 21, 2024. This occurred before the deadline of August 1, 2024. Therefore, the prediction is true.", "target_date": "2024-07-31T23:59:59Z", "target_value": None, "current_value": None, "direction_inferred": None, "sources": ["Google Search", "coingecko", "coinmarketcap", "coinbase", "https://en.wikipedia.org/wiki/Withdrawal_of_Joe_Biden_from_the_2024_United_States_presidential_election", "https://www.texastribune.org/2024/07/19/biden-texas-presidential-ballot-election-law/", "https://www.cnn.com/politics/live-news/joe-biden-election-drop-out-07-22-24", "https://www.dispatch.com/story/news/politics/elections/2024/07/21/biden-dropped-out-will-harris-another-democrat-make-the-ohio-ballot/74490691007/", "https://ballotpedia.org/State_laws_and_party_rules_on_replacing_a_presidential_nominee,_2024"]},
{"statement": "Will Bitcoin close above $100,000 by October 10, 2025?", "resolution": "PENDING", "confidence": 100, "summary": "The prediction is about whether Bitcoin will close above $100,000 by October 10, 2025. The current date is June 26, 2025, and the market close date is October 10, 2025. The current price of Bitcoin is $107,341, which is above the $100,000 threshold. However, the prediction is about the closing price on October 10, 2025. Since the target date is in the future and the closing price on that date is unknown, the prediction remains pending. The prediction is pending.", "target_date": "2025-10-10T00:00:00Z", "target_value": 100000, "current_value": 107341, "direction_inferred": "above", "sources": ["CoinGecko", "reuters", "binance", "coinbase", "kraken"]},
{"statement": "Will Bitcoin close above $60,000 by July 21, 2025?", "resolution": "PENDING", "confidence": 100, "summary": "The prediction is about whether Bitcoin will close above $60,000 by July 21, 2025. The current date is June 26, 2025, and the market close date is still in the future. Although the current price of Bitcoin is $107,339, which is above $60,000, the prediction is about the closing price on July 21, 2025. Since the target date has not yet arrived, the prediction remains pending. The prediction is pending.", "target_date": "2025-07-21T00:00:00Z", "target_value": 60000, "current_value": 107339, "direction_inferred": "above", "sources": ["CoinGecko","reuters", "binance", "coinbase", "kraken"]},
{"statement": "Will the betting favorite win the 2024 Belmont Stakes?", "resolution": "TRUE", "confidence": 100, "summary": "Dornoch, the betting favorite, won the 2024 Belmont Stakes. This confirms the prediction as true.", "target_date": None, "target_value": None, "current_value": None, "direction_inferred": None, "sources": ["Google Search", "reuters", "binance", "coinbase", "kraken", "https://sports.yahoo.com/horse-racing/breaking-news/live/belmont-stakes-2025-recap-winnings-sovereignty-beats-out-journalism-in-rematch-of-kentucky-derby-preakness-winners-200048971.html", "https://www.espn.com/espn/betting/story/_/id/45451378/belmont-stakes-2025-betting-odds-favorites-horse-racing-triple-crown-storylines", "https://www.app.com/story/sports/horses/2025/06/05/belmont-stakes-betting-guide-2025-expert-picks-odds-analysis/83879176007/", "https://www.latimes.com/sports/live/belmont-stakes-live-updates-start-time-betting-odds-results", "https://www.cbssports.com/general/news/belmont-stakes-2024-odds-picks-post-draw-mystik-dan-seize-the-grey-mindframe-sierra-leone-predictions/"]},
{"statement": "Will Bitcoin close above $70,000 by June 03, 2025?", "resolution": "PENDING", "confidence": 100, "summary": "The prediction is about whether Bitcoin will close above $70,000 by June 03, 2025. The current date is after the target date, but there is no information available on whether Bitcoin crossed the $70,000 threshold before the market close date. Without confirmation of the threshold crossing, the prediction remains unresolved. The prediction is PENDING.", "target_date": "2025-06-03T00:00:00Z", "target_value": 70000, "current_value": 107087, "direction_inferred": "above", "sources": ["CoinGecko","reuters", "binance", "coinbase", "kraken"]},
{"statement": "Will Bitcoin close above $130,000 by June 26, 2025?", "resolution": "FALSE", "confidence": 100, "summary": "The market closed on June 26, 2025, and the current price of Bitcoin is $107,113, which is below the $130,000 threshold. There is no evidence that Bitcoin ever crossed the $130,000 threshold before the market closed. The prediction is false.", "target_date": "2025-06-26T00:00:00Z", "target_value": 130000, "current_value": 107113, "direction_inferred": "above", "sources": ["CoinGecko","reuters", "binance", "coinbase", "kraken"]},
{"statement": "Will Bitcoin close above $90,000 by September 24, 2025?", "resolution": "PENDING", "confidence": 100, "summary": "The prediction is about whether Bitcoin will close above $90,000 by September 24, 2025. The current date is June 27, 2025, and the market close date is September 24, 2025. The current price of Bitcoin is $107,317, which is above the $90,000 threshold. However, the prediction is about the closing price on the target date, which is still in the future. Therefore, the prediction remains pending as the target date has not yet arrived.", "target_date": "2025-09-24T00:00:00Z", "target_value": 90000, "current_value": 107317, "direction_inferred": "above", "sources": ["CoinGecko", "coinmarketcap", "coinbase", "reuters", "binance", "coinbase", "kraken"]},
{"statement": "Will Bitcoin close above $120,000 by September 15, 2025?", "resolution": "PENDING", "confidence": 100, "summary": "The prediction is about whether Bitcoin will close above $120,000 by September 15, 2025. The current date is June 27, 2025, which is before the target date. The current price of Bitcoin is $107,377, and there is no information indicating that the threshold of $120,000 has been crossed at any point. Since the end date has not yet arrived and the threshold has not been crossed, the prediction remains pending.", "target_date": "2025-09-15T00:00:00Z", "target_value": 120000, "current_value": 107377, "direction_inferred": "above", "sources": ["CoinGecko", "coinmarketcap", "coinbase", "reuters", "binance", "coinbase", "kraken"]},
{"statement": "Will Bitcoin close above $130,000 by May 01, 2025?", "resolution": "FALSE", "confidence": 100, "summary": "The market closed on May 01, 2025, and the current price of Bitcoin is $107,428, which is below the $130,000 threshold. There is no evidence that Bitcoin ever crossed the $130,000 threshold before the market closed. The prediction is false.", "target_date": "2025-05-01T00:00:00Z", "target_value": 130000, "current_value": 107428, "direction_inferred": "above", "sources": ["CoinGecko", "coinmarketcap", "coinbase", "reuters", "binance", "coinbase", "kraken"]},
{"statement": "Will Bitcoin close above $70,000 by March 22, 2025?", "resolution": "FALSE", "confidence": 100, "summary": "The prediction required Bitcoin to close above $70,000 by March 22, 2025. The current time is past the target date, and there is no information confirming that Bitcoin closed above $70,000 by the specified date. The prediction is false.", "target_date": "2025-03-22T00:00:00Z", "target_value": 70000, "current_value": 107504, "direction_inferred": "above", "sources": ["CoinGecko", "coinmarketcap", "coinbase", "reuters", "binance", "coinbase", "kraken"]}
]

for ret in result:
    insert_data(ret["statement"], ret)
# Example usage
# insert_data("Hello", {"reply": "Hi there!", "emotion": "happy", "confidence": 90})
# insert_data("What's your name?", {"reply": "I'm ChatGPT.", "emotion": "neutral", "confidence": 80})
# ret = get_response("What's your name?")
# print(ret)