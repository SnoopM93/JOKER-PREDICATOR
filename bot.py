import discord
from discord.ext import tasks
import requests
import datetime

# --- CONFIG ---
TOKEN = "METS_TON_TOKEN_DISCORD_ICI"
API_KEY = "METS_TA_CLE_API_FOOTBALL_ICI"
CHANNEL_ID = 1216885799216484413

headers = {"x-apisports-key": API_KEY}
intents = discord.Intents.default()
client = discord.Client(intents=intents)

def get_team_avg_corners(team_id):
    # 5 derniers matchs RÉELS
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

def build_prediction():
    today = datetime.date.today().strftime("%Y-%m-%d")
    url = f"https://v3.football.api-sports.io/fixtures?date={today}&league=39&season=2024"
    resp = requests.get(url, headers=headers).json()
    fixtures = resp['response'][:5]
    
    if not fixtures:
        return f"**🔮 JOKER-PREDICTOR V3 - {today}**\nPas de matchs PL aujourd'hui."
    
    msg = f"**🔮 JOKER-PREDICTOR V3 - {today} - 0% RANDOM**\n_Vraies stats API, pas comme XX EMPEREUR_\n\n"
    for f in fixtures:
        home = f['teams']['home']['name']
        away = f['teams']['away']['name']
        home_id = f['teams']['home']['id']
        away_id = f['teams']['away']['id']
        
        home_avg = get_team_avg_corners(home_id)
        away_avg = get_team_avg_corners(away_id)
        total = round(home_avg + away_avg, 1)
        
        if total >= 11:
            pred = f"Over 9.5 {int(60+total)}% ✅ HAUTE"
        else:
            pred = f"Under 9.5 {int(65-total)}%"
            
        msg += f"**{home} vs {away}**\n"
        msg += f"├─ 🟨 Corners: {total} ({home_avg:.1f}+{away_avg:.1f}) | {pred}\n"
        msg += f"└─ 📊 Bas
