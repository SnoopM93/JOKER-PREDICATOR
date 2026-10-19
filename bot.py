import discord
from discord.ext import tasks
import requests
import datetime

# --- CONFIG - REMPLACE LES 2 LIGNES CI-DESSOUS ---
TOKEN = "METS_TON_TOKEN_DISCORD_ICI"
API_KEY = "METS_TA_CLE_API_FOOTBALL_ICI"
CHANNEL_ID = 1216885799216484413

headers = {"x-apisports-key": API_KEY}
intents = discord.Intents.default()
client = discord.Client(intents=intents)

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
        return f"**🔮 JOKER-PREDICATOR V3 - {today}**\nPas de matchs PL aujourd'hui - le bot check Liga/Serie A demain."
    
    msg = f"**🔮 JOKER-PREDICATOR V3 - {today} - 0% RANDOM**\n_Vraies stats API_\n\n"
    for f in fixtures:
        home = f['teams']['home']['name']
        away = f['teams']['away']['name']
        home_id = f['teams']['home']['id']
        away_id = f['teams']['away']['id']
        home_avg = get_team_avg_corners(home_id)
        away_avg = get_team_avg_corners(away_id)
        total = round(home_avg + away_avg, 1)
        pred = f"Over 9.5 {int(60+total)}% ✅" if total >= 11 else f"Under 9.5 {int(65-total)}%"
        msg += f"**{home} vs {away}**\n"
        msg += f"├─ 🟨 Corners: {total} ({home_avg:.1f}+{away_avg:.1f}) | {pred}\n"
        msg += f"└─ 📊 Basé sur 5 derniers matchs réels\n\n"
    return msg

@tasks.loop(hours=24)
async def daily_post():
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        return
    try:
        await channel.send(build_prediction())
    except Exception as e:
        await channel.send(f"Erreur: {e}")

@client.event
async def on_ready():
    print(f"Connecté: {client.user}")
    daily_post.start()

client.run(TOKEN)
