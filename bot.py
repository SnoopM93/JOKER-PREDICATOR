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

app = Flask(__name__)
@app.route('/')
def home(): return "JOKER AI Online"
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
    if not fixtures: return f"**🔮 JOKER V5 - {today}**\nPas de matchs."
    msg=f"**🔮 JOKER-PRONOSTIC V5 - {today}**\n\n"
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
    print(f"Connecté: {bot.user} V5 AI")
    if not daily_post.is_running(): daily_post.start()

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)
    
    if bot.user.mentioned_in(message) or "joker" in message.content.lower():
        question = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not question: question = "Salut"

        # Si c'est une demande de prono, on donne les vrais chiffres
        if any(x in question.lower() for x in ["corner","but","prono","match"]):
            await message.reply(build_prediction())
            return

        # SINON, il répond comme moi, avec une IA
        if groq_client:
            try:
                async with message.channel.typing():
                    completion = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role":"system","content":"Tu es JOKER-PRONOSTIC, un assistant IA expert en paris sportifs, sympa, tu parles comme un pote de Lomé, un peu d'argot, tu aides pour corners et buts mais tu peux parler de tout. Réponds court."},
                            {"role":"user","content":question}
                        ]
                    )
                    await message.reply(completion.choices[0].message.content[:1900])
            except Exception as e:
                await message.reply(f"Mon cerveau IA bug un peu: {e}\nMais tape `!joker` pour le prono.")
        else:
            await message.reply("Ajoute ta clé GROQ_API_KEY sur Render pour que je devienne intelligent comme ChatGPT !")

@bot.command()
async def joker(ctx): await ctx.send(build_prediction())

bot.run(TOKEN)
