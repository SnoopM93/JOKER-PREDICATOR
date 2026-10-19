import discord
from discord.ext import commands, tasks
import requests, datetime, os
from flask import Flask
import threading
from groq import Groq

TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
CHANNEL_ID = 1216885799216484413

headers = {"x-apisports-key": API_KEY}
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None
conversations = {}

app = Flask(__name__)
@app.route('/')
def home(): return "JOKER V6.5 PRO CORNERS"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_flask).start()

def get_team_stats(team_id):
    try:
        url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5"
        r = requests.get(url, headers=headers).json()
        corners=[]; buts=[]
        for f in r.get('response',[])[:5]:
            fid=f['fixture']['id']
            stat=requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fid}", headers=headers).json()
            for ts in stat.get('response',[]):
                if ts['team']['id']==team_id:
                    for s in ts['statistics']:
                        if s['type']=='Corner Kicks' and s['value']: corners.append(int(s['value']))
                        if s['type']=='Goals' and s['value'] is not None: buts.append(int(s['value']))
        return sum(corners)/len(corners) if corners else 4.5, sum(buts)/len(buts) if buts else 1.2
    except: return 4.5, 1.2

def build_prediction():
    today=datetime.date.today().strftime("%Y-%m-%d")
    url=f"https://v3.football.api-sports.io/fixtures?date={today}&league=39&season=2024"
    try: fixtures=requests.get(url, headers=headers).json().get('response',[])[:5]
    except: return "Erreur API"
    if not fixtures: return f"**🔮 JOKER V6.5 - {today}**\
