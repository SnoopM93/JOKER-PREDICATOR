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
def home(): return "JOKER V6.8.1 FULL"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_flask).start()

def get_team_stats(team_id):
    try:
        url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5"
        r = requests.get(url, headers=headers).json()
        corners=[]; buts_marques=[]; buts_encaisses=[]
        for f in r.get('response',[])[:5]:
            fid=f['fixture']['id']
            goals_home=f['goals']['home']; goals_away=f['goals']['away']
            if goals_home is None or goals_away is None: continue
            is_home=f['teams']['home']['id']==team_id
            if is_home: buts_marques.append(goals_home); buts_encaisses.append(goals_away)
            else: buts_marques.append(goals_away); buts_encaisses.append(goals_home)
            stat=requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fid}", headers=headers).json()
            for ts in stat.get('response',[]):
                if ts['team']['id']==team_id:
                    for s in ts['statistics']:
                        if s['type']=='Corner Kicks' and s['value']:
                            try: corners.append(int(s['value']))
                            except: pass
        avg_c=sum(corners)/len(corners) if corners else 4.5
        avg_m=sum(buts_marques)/len(buts_marques) if buts_marques else 1.1
        avg_e=sum(buts_encaisses)/len(buts_encaisses) if buts_encaisses else 1.1
        return avg_c, avg_m, avg_e
    except: return 4.5, 1.1, 1.1

def format_date(iso):
    try:
        dt=datetime.datetime.fromisoformat(iso.replace("Z","+00:00"))
        return dt.strftime("%d/%m/%Y a %H:%M UTC")
    except: return iso

def build_prediction():
    today=datetime.date.today().strftime("%Y-%m-%d")
    url=f"https://v3.football.api-sports.io/fixtures?date={today}&league=39&season=2024"
    try: fixtures=requests.get(url, headers=headers).json().get('response',[])[:5]
    except: return "Erreur API"
    if not fixtures: return f"JOKER V6.8.1 - {today} - Pas de PL, tag moi"
    msg=f"JOKER V6.8.1 FULL - {today}\n\n"
    for f in fixtures:
        home=f['teams']['home']['name']; away=f['teams']['away']['name']
        hc,h_m,h_e=get_team_stats(f['teams']['home']['id'])
        ac,a_m,a_e=get_team_stats(f['teams']['away']['id'])
        tc=round(hc+ac,1)
        score_h=round((h_m+a_e)/2); score_a=round((a_m+h_e)/2)
        date_str=format_date(f['fixture']['date'])
        msg+=f"{home} vs {away}\n- Date: {date_str}\n- Score calcule: {score_h}-{score_a}\n- Corners: {tc} ({hc:.1f}+{ac:.1f})\n- Buts: D {h_m:.1f} vs E {a_e:.1f}\n\n"
    return msg

@tasks.loop(time=datetime.time(hour=9, minute=0, tzinfo=datetime.timezone.utc))
async def daily_post():
    c=bot.get_channel(CHANNEL_ID)
    if c: await c.send(build_prediction())

@bot.event
async def on_ready():
    print(f"Connecte V6.8.1 FULL")
    if not daily_post.is_running(): daily_post.start()

@bot.event
async def on_message(message):
    if message.author==bot.user: return
    await bot.process_commands(message)
    if bot.user.mentioned_in(message) or "joker" in message.content.lower():
        user_id=message.author.id
        question=message.content.replace(f"<@{bot.user.id}>","").strip()
        if not question: question="Salut"
        if any(x in question.lower() for x in ["!joker","!corners","!buts","prono du jour"]):
            await message.reply(build_prediction())
            return
        if user_id not in conversations: conversations[user_id]=[]
        conversations[user_id].append({"role":"user","content":question})
        if len(conversations[user_id])>12: conversations[user_id]=conversations[user_id][-12:]
        if groq_client:
            try:
                async with message.channel.typing():
                    system_prompt = """
Tu es JOKER-PRONOSTIC V6.8.1 FULL, expert de Lome, specialiste SCORE + CORNERS + BUTS.
REGLES:
1. Toujours en FRANCAIS
2. PAS DE HASARD, 100% STATS REELLES
3. FORMAT PRO complet avec TOUT: date, score, corners, tableau

FORMAT OBLIGATOIRE A GARDER:

**[Equipe A vs Equipe B] - Analyse PRO**

**Date et Heure**
- Date: JJ/MM/AAAA a HH:MM UTC (si tu ne l'as pas, mets "Date: A confirmer - verifie calendrier")

**Score calcule (pas de hasard)**
- Domicile marque: X.X/match, encaisse: Y.Y
- Exterieur marque: X.X, encaisse: Y.Y
- Calcul: (marques D + encaisses E)/2
- Score final: 1-0

**Result odds**
- 1 / X / 2

**Corners**
- Total calcule: 5.2 + 4.3 = 9.5
- Over 9.5: OUI/NON

**Handicap & Buts**
- Domicile -0.5
- Exterieur +0.5 -> Victoire ou Nul = tu gagnes
- Over 2.5 buts

**Pro-tip Tableau**
| Parier | Pourquoi | Astuce | Cote |
|---|---|---|---|
| Score 1-0 | Stats 1.1 vs 1.2 | Calcule | 6.50 |
| Over 9.5 corners | 9.5 calcules | SAFE | 1.85 |
| Handicap +0.5 | Assurance | Value | 1.90 |

**Points cles**
- Domicile: X buts / Y corners
- Exterieur: X buts / Y corners

**Quick take**
SAFE: ... | SCORE: ... | QUI PAIE: ...

Tu gardes TOUT: date, score, corners, tableau. Jamais enlever.
"""
                    history=[{"role":"system","content":system_prompt}] + conversations[user_id]
                    completion=groq_client.chat.completions.create(model="openai/gpt-oss-20b", messages=history)
                    reponse=completion.choices[0].message.content
                    conversations[user_id].append({"role":"assistant","content":reponse})
                    await message.reply(reponse[:1900])
            except Exception as e: await message.reply(f"Erreur: {e}")

@bot.command()
async def joker(ctx): await ctx.send(build_prediction())
@bot.command()
async def corners(ctx): await ctx.send(build_prediction())
@bot.command()
async def buts(ctx): await ctx.send(build_prediction())
@bot.command()
async def reset(ctx):
    if ctx.author.id in conversations: del conversations[ctx.author.id]
    await ctx.send("Memoire effacee boss!")

bot.run(TOKEN)
