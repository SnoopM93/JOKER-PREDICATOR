import discord
from discord.ext import tasks
import requests
import datetime

# --- TA CONFIG (remplace juste ces 2 lignes) ---
TOKEN = "METS_TON_TOKEN_DISCORD_ICI"
API_KEY = "METS_TA_CLE_API_FOOTBALL_ICI"
CHANNEL_ID = 1216885799216484413

headers = {"x-apisports-key": API_KEY}
