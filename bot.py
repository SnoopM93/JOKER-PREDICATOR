import discord
from discord.ext import tasks
import requests
import datetime
import os
from flask import Flask
import threading

TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
CHANNEL_ID = 1216885799216484413

headers = {"x-apisports-key": API_KEY}
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# --- Petit serveur web pour Render gratuit ---
app = Flask(__name__)
@app.route('/')
def home():
    return "JOKER-PREDICATOR is alive!"
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_flask).start()
# --------------------------------------------

def get_team_avg_corners(team_id):
    try:
        url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5"
        r = requests.get(url, headers=headers).json()
        corners = []
        for f in r['response']:
            fid = f['fixture']['id']
            stat_url = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fid}"
            stat_r = requests.get(stat_url, headers=headers).json()
            for team_stat in stat_r['response']:
                if team_stat['team']['id'] == team_id:
                    for s in team_stat['statistics']:
                        if s['type'] == 'Corner Kicks' and s['value']:
                            corners.append(int(s['value']))
        return sum(corners) / len(corners) if corners else 5.0
    except:
        return 5.0

def build_prediction():
    today = datetime.date.today().strftime("%Y-%m-%d")
    url = f"https://v3.football.api-sports.io/fixtures?date={today}&league=39&season=2024"
    fixtures = requests.get(url, headers=headers).json()['response'][:5]
    if not fixtures:
        return f"**🔮 JOKER-PREDICATOR V3 - {today}**\nPas de matchs PL."
    msg = f"**🔮 JOKER-PREDICATOR V3 - {today}**\n\n"
    for f in fixtures:
        home = f['teams']['home']['name']
        away = f['teams']['away']['name']
        total = round(get_team_avg_corners(f['teams']['home']['id']) + get_team_avg_corners(f['teams']['away']['id']),1)
        pred = f"Over 9.5 {int(60+total)}% ✅" if total >= 11 else f"Under 9.5"
        msg += f"**{home} vs {away}**\nCorners: {total} | {pred}\n\n"
    return msg

@tasks.loop(hours=24)
async def daily_post():
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(build_prediction())

@client.event
async def on_ready():
    print(f"Connecté: {client.user}")
    daily_post.start()

client.run(TOKEN)
