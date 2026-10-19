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
def home(): return "JOKER V6.3 FR Online"
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
    if not fixtures: return f"**🔮 JOKER V6.3 - {today}**\nPas de matchs PL aujourd'hui, mais demande moi n'importe quel match (ex: Getafe vs Rayo) et je t'analyse ça !"
    msg=f"**🔮 JOKER-PRONOSTIC V6.3 - {today}**\n\n"
    for f in fixtures:
        home=f['teams']['home']['name']; away=f['teams']['away']['name']
        hc,hb=get_team_stats(f['teams']['home']['id']); ac,ab=get_team_stats(f['teams']['away']['id'])
        tc=round(hc+ac,1); tb=round((hb+ab)/2,1)
        msg+=f"**{home} vs {away}**\n├─ 🟨 Corners: {tc} -> {'Over 9.5 ✅' if tc>=10.5 else 'Under'}\n└─ ⚽ Buts: ~{tb} -> {'Over 2.5 ✅' if tb>=1.5 else 'Under'}\n\n"
    return msg

@tasks.loop(time=datetime.time(hour=9, minute=0, tzinfo=datetime.timezone.utc))
async def daily_post():
    c=bot.get_channel(CHANNEL_ID)
    if c: await c.send(build_prediction())

@bot.event
async def on_ready():
    print(f"Connecté: {bot.user} V6.3 FR")
    if not daily_post.is_running(): daily_post.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)
    
    if bot.user.mentioned_in(message) or "joker" in message.content.lower():
        user_id = message.author.id
        question = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not question: question = "Salut"

        if any(x in question.lower() for x in ["!joker","!corners","!buts","prono du jour","corners du jour","buts du jour"]):
            await message.reply(build_prediction())
            return

        if user_id not in conversations: conversations[user_id] = []
        conversations[user_id].append({"role":"user","content":question})
        if len(conversations[user_id]) > 12: conversations[user_id] = conversations[user_id][-12:]

        if groq_client:
            try:
                async with message.channel.typing():
                    history = [
                        {"role":"system","content":"Tu es JOKER-PRONOSTIC, expert paris sportifs, pote de Lomé au Togo. RÈGLE NUMÉRO 1 ABSOLUE ET NON NÉGOCIABLE: Tu réponds TOUJOURS en FRANÇAIS. Même si on te parle en anglais, tu réponds en français. Utilise un français simple avec un peu d'argot togolais (boss, mon frère, c'est géré). Tu te souviens de toute la conversation. Tu peux parler de tout mais ton expertise c'est les pronos corners et buts avec vraies stats API-Football. Tes réponses doivent être courtes (3-5 lignes) sauf si on demande une longue analyse. JAMAIS d'anglais sauf si l'utilisateur écrit exactement 'parle en anglais'."}
                    ] + conversations[user_id]

                    completion = groq_client.chat.completions.create(
                        model="openai/gpt-oss-20b",
                        messages=history
                    )
                    reponse = completion.choices[0].message.content
                    conversations[user_id].append({"role":"assistant","content":reponse})
                    await message.reply(reponse[:1900])
            except Exception as e:
                await message.reply(f"Erreur IA: {e}")
        else:
            await message.reply("Ajoute GROQ_API_KEY sur Render!")

@bot.command()
async def joker(ctx): await ctx.send(build_prediction())
@bot.command()
async def corners(ctx): await ctx.send(build_prediction())
@bot.command()
async def buts(ctx): await ctx.send(build_prediction())
@bot.command()
async def reset(ctx):
    if ctx.author.id in conversations: del conversations[ctx.author.id]
    await ctx.send("🧠 Mémoire effacée boss!")

bot.run(TOKEN)
