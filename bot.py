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
def home(): return "JOKER V6.8.3"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_flask).start()

def get_team_stats(team_id):
    try:
        url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5"
        r = requests.get(url, headers=headers).json()
        corners=[]; buts_marques=[]; buts_encaisses=[]
        for f in r.get('response',[])[:5]:
            fid=f['fixture']['id']
            gh=f['goals']['home']; ga=f['goals']['away']
            if gh is None or ga is None: continue
            is_home=f['teams']['home']['id']==team_id
            if is_home: buts_marques.append(gh); buts_encaisses.append(ga)
            else: buts_marques.append(ga); buts_encaisses.append(gh)
            stat=requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fid}", headers=headers).json()
            for ts in stat.get('response',[]):
                if ts['team']['id']==team_id:
                    for s in ts['statistics']:
                        if s['type']=='Corner Kicks' and s['value']:
                            try: corners.append(int(s['value']))
                            except: pass
        avg_c=sum(corners)/len(corners) if corners else 4.5
        avg_m=sum(buts_marques)/len(buts_marques) if buts_marques else 1.0
        avg_e=sum(buts_encaisses)/len(buts_encaisses) if buts_encaisses else 1.2
        return avg_c, avg_m, avg_e
    except: return 4.5, 1.0, 1.2

def format_date(iso):
    try:
        dt=datetime.datetime.fromisoformat(iso.replace("Z","+00:00"))
        return dt.strftime("%d/%m/%Y a %H:%M UTC")
    except: return iso

def get_team_id_by_name(name):
    try:
        url=f"https://v3.football.api-sports.io/teams?search={name}"
        r=requests.get(url, headers=headers).json()
        if r.get('response'):
            return r['response'][0]['team']['id'], r['response'][0]['team']['name']
    except: pass
    return None, None

def get_fixture_info(query):
    # Cherche 2 equipes dans la question
    words = [w for w in query.replace("vs"," ").replace(" "," ").split() if len(w)>=3]
    team1_id=team1_name=None
    team2_id=team2_name=None
    found=[]
    for w in words:
        tid, tname = get_team_id_by_name(w)
        if tid and tid not in [x[0] for x in found]:
            found.append((tid, tname))
            if len(found)>=2: break
    if len(found)>=2:
        team1_id, team1_name = found[0]
        team2_id, team2_name = found[1]
        # Cherche le prochain face a face
        url=f"https://v3.football.api-sports.io/fixtures?team={team1_id}&next=10"
        fixtures=requests.get(url, headers=headers).json().get('response',[])
        for f in fixtures:
            h_id=f['teams']['home']['id']; a_id=f['teams']['away']['id']
            if (h_id==team2_id or a_id==team2_id):
                date_str=format_date(f['fixture']['date'])
                return date_str, team1_id, team1_name, team2_id, team2_name
        # Sinon prend le prochain match de team1
        if fixtures:
            date_str=format_date(fixtures[0]['fixture']['date'])
            return date_str, team1_id, team1_name, team2_id, team2_name
    elif len(found)==1:
        team1_id, team1_name = found[0]
        url=f"https://v3.football.api-sports.io/fixtures?team={team1_id}&next=1"
        fixtures=requests.get(url, headers=headers).json().get('response',[])
        if fixtures:
            date_str=format_date(fixtures[0]['fixture']['date'])
            h_name=fixtures[0]['teams']['home']['name']
            a_name=fixtures[0]['teams']['away']['name']
            # Cherche team2 id
            other_name = a_name if team1_id==fixtures[0]['teams']['home']['id'] else h_name
            tid2, _ = get_team_id_by_name(other_name.split()[0])
            return date_str, team1_id, team1_name, tid2, other_name
    return None, None, None, None, None

def build_prediction():
    today=datetime.date.today().strftime("%Y-%m-%d")
    year=datetime.date.today().year
    season=year if datetime.date.today().month >=8 else year-1
    url=f"https://v3.football.api-sports.io/fixtures?date={today}&league=39&season={season}"
    try: fixtures=requests.get(url, headers=headers).json().get('response',[])[:5]
    except: return "Erreur API"
    if not fixtures: return f"JOKER V6.8.3 - {today} - Pas de PL"
    msg=f"JOKER V6.8.3 - {today}\n\n"
    for f in fixtures:
        home=f['teams']['home']['name']; away=f['teams']['away']['name']
        hc,h_m,h_e=get_team_stats(f['teams']['home']['id'])
        ac,a_m,a_e=get_team_stats(f['teams']['away']['id'])
        tc=round(hc+ac,1)
        sh=round((h_m+a_e)/2); sa=round((a_m+h_e)/2)
        date_str=format_date(f['fixture']['date'])
        msg+=f"{home} vs {away}\n- Date: {date_str}\n- Score: {sh}-{sa}\n- Corners: {tc}\n\n"
    return msg

@tasks.loop(time=datetime.time(hour=9, minute=0, tzinfo=datetime.timezone.utc))
async def daily_post():
    c=bot.get_channel(CHANNEL_ID)
    if c: await c.send(build_prediction())

@bot.event
async def on_ready():
    print("V6.8.3 ready")
    if not daily_post.is_running(): daily_post.start()

@bot.event
async def on_message(message):
    if message.author==bot.user: return
    await bot.process_commands(message)
    if bot.user.mentioned_in(message) or "joker" in message.content.lower():
        q=message.content.replace(f"<@{bot.user.id}>","").strip()
        if not q: q="Salut"
        if any(x in q.lower() for x in ["!joker","!corners","!buts","prono du jour"]):
            await message.reply(build_prediction())
            return
        uid=message.author.id
        if uid not in conversations: conversations[uid]=[]
        conversations[uid].append({"role":"user","content":q})
        if len(conversations[uid])>12: conversations[uid]=conversations[uid][-12:]
        if groq_client:
            try:
                async with message.channel.typing():
                    date_str, t1_id, t1_name, t2_id, t2_name = get_fixture_info(q)
                    if not date_str: date_str="A venir - verifie calendrier"
                    
                    # CALCULE LES VRAIES STATS ICI, PAS DANS LLM
                    if t1_id and t2_id:
                        hc,h_m,h_e = get_team_stats(t1_id)
                        ac,a_m,a_e = get_team_stats(t2_id)
                        tc = round(hc+ac,1)
                        calc_h = round((h_m + a_e)/2,2)
                        calc_a = round((a_m + h_e)/2,2)
                        score_h = round(calc_h)
                        score_a = round(calc_a)
                        stats_block = f"""
STATS REELLES API (ne pas inventer):
- {t1_name} (Domicile): marque {h_m:.2f}/match, encaisse {h_e:.2f}, corners {hc:.2f}
- {t2_name} (Exterieur): marque {a_m:.2f}/match, encaisse {a_e:.2f}, corners {ac:.2f}
- Total corners: {hc:.2f} + {ac:.2f} = {tc}
- Calcul Score Domicile: ({h_m:.2f} + {a_e:.2f}) / 2 = {calc_h} -> {score_h}
- Calcul Score Exterieur: ({a_m:.2f} + {h_e:.2f}) / 2 = {calc_a} -> {score_a}
- SCORE FINAL CALCULE: {score_h}-{score_a}
- DATE REELLE: {date_str}
"""
                    else:
                        stats_block = f"DATE: {date_str} - Stats non trouvees, utilise valeurs moyennes"
                        hc=h_m=h_e=ac=a_m=a_e=0
                        tc=9.5; score_h=1; score_a=0

                    system_prompt = f"""
Tu es JOKER-PRONOSTIC V6.8.3
Tu DOIS utiliser les STATS REELLES ci-dessous, INTERDIT d'inventer.

{stats_block}

REGLES:
1. Francais uniquement
2. PAS DE LATEX, utilise -> pas \\Rightarrow
3. Utilise EXACTEMENT les chiffres fournis ci-dessus pour le calcul
4. Date obligatoire: {date_str}

FORMAT:

**[{t1_name if t1_name else 'Equipe A'} vs {t2_name if t2_name else 'Equipe B'}] - Analyse PRO**

**Date et Heure**
- {date_str}

**Score calcule (pas de hasard)**
- Domicile ({t1_name}): marque {h_m if t1_id else 'X'}/match, encaisse {h_e if t1_id else 'Y'}
- Exterieur ({t2_name}): marque {a_m if t2_id else 'X'}, encaisse {a_e if t2_id else 'Y'}
- Calcul: ({h_m if t1_id else 'X'} + {a_e if t2_id else 'Y'})/2 = {calc_h if t1_id and t2_id else '...'} -> {score_h if t1_id and t2_id else '1'} et ({a_m if t1_id and t2_id else 'X'} + {h_e if t1_id and t2_id else 'Y'})/2 = {calc_a if t1_id and t2_id else '...'} -> {score_a if t1_id and t2_id else '0'}
- Score final: {score_h if t1_id and t2_id else '1'}-{score_a if t1_id and t2_id else '0'}

**Result odds**
- 1 / X / 2

**Corners**
- {hc if t1_id else 4.5} + {ac if t2_id else 4.5} = {tc if t1_id and t2_id else 9.5}

**Handicap & Buts**
**Pro-tip Tableau**
| Parier | Pourquoi | Astuce | Cote |
|---|---|---|---|
**Points cles**
**Quick take**
"""
                    history=[{"role":"system","content":system_prompt}] + conversations[uid]
                    comp=groq_client.chat.completions.create(model="openai/gpt-oss-20b", messages=history)
                    rep=comp.choices[0].message.content
                    conversations[uid].append({"role":"assistant","content":rep})
                    await message.reply(rep[:1900])
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
    await ctx.send("Memoire effacee!")

bot.run(TOKEN)
