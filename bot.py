import discord
from discord.ext import commands, tasks
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
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

app = Flask(__name__)
@app.route('/')
def home(): return "JOKER CORNERS + BUTS Online"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_flask).start()

def get_team_stats(team_id):
    try:
        url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5"
        r = requests.get(url, headers=headers).json()
        corners=[]; buts=[]
        for f in r.get('response',[]):
            fid=f['fixture']['id']
            stat=requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fid}", headers=headers).json()
            for ts in stat.get('response',[]):
                if ts['team']['id']==team_id:
                    for s in ts['statistics']:
                        if s['type']=='Corner Kicks' and s['value']: corners.append(int(s['value']))
                        if s['type']=='Total Shots' and s['value']: buts.append(int(s['value'])) # On estime buts via tirs
                        if s['type']=='Goals' and s['value'] is not None: # Si l'API donne les buts
                           try: buts.append(int(s['value']))
                           except: pass
        avg_c = sum(corners)/len(corners) if corners else 4.5
        avg_b = sum(buts)/len(buts) if buts else 1.2
        return avg_c, avg_b
    except:
        return 4.5, 1.2

def build_prediction():
    today=datetime.date.today().strftime("%Y-%m-%d")
    url=f"https://v3.football.api-sports.io/fixtures?date={today}&league=39&season=2024"
    try: fixtures=requests.get(url, headers=headers).json().get('response',[])[:5]
    except: return "Erreur API Football"
    if not fixtures: return f"**🔮 JOKER V4 - {today}**\nPas de matchs PL aujourd'hui."
    
    msg=f"**🔮 JOKER-PRONOSTIC V4 - CORNERS & BUTS - {today}**\n\n"
    for f in fixtures:
        home=f['teams']['home']['name']; away=f['teams']['away']['name']
        hc, hb = get_team_stats(f['teams']['home']['id'])
        ac, ab = get_team_stats(f['teams']['away']['id'])
        
        total_corners = round(hc + ac, 1)
        total_buts_est = round((hb+ab)/2, 1) # moyenne buts
        
        pred_corner = f"Over 9.5 ({int(60+total_corners)}%) ✅" if total_corners>=10.5 else f"Under 9.5"
        pred_but = f"Over 2.5 buts ({int(55+total_buts_est*5)}%) ✅" if total_buts_est>=1.5 else f"Under 2.5"
        
        msg+=f"**{home} vs {away}**\n"
        msg+=f"├─ 🟨 Corners: {total_corners} -> {pred_corner}\n"
        msg+=f"└─ ⚽ Buts: ~{total_buts_est} -> {pred_but}\n\n"
    return msg

@tasks.loop(time=datetime.time(hour=9, minute=0, tzinfo=datetime.timezone.utc))
async def daily_post():
    channel=bot.get_channel(CHANNEL_ID)
    if channel: await channel.send(build_prediction())

@bot.event
async def on_ready():
    print(f"Connecté: {bot.user} V4 CORNERS+BUTS")
    if not daily_post.is_running(): daily_post.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)
    c = message.content.lower()
    if bot.user.mentioned_in(message) or "joker" in c or "corner" in c or "but" in c:
        if "corner" in c or "but" in c or "prono" in c:
            await message.reply(build_prediction())
        else:
            await message.reply(f"Yo {message.author.mention} ! Tu veux corners ou buts ? Tape `!corners` `!buts` `!joker`")

@bot.command()
async def corners(ctx): await ctx.send(build_prediction())
@bot.command()
async def buts(ctx): await ctx.send(build_prediction())
@bot.command()
async def joker(ctx): await ctx.send(build_prediction())

bot.run(TOKEN)
