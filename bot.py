import discord
from discord.ext import commands
import requests
import csv
import io
import os  # Ajouté pour lire les variables d'environnement sur Render

# Forcer Python à utiliser uniquement l'IPv4 pour Supercell
from urllib3.util import connection
_orig_create_connection = connection.create_connection

def patched_create_connection(address, *args, **kwargs):
    host, port = address
    return _orig_create_connection((host, port), *args, socket_options=[(6, 1, 0)])

connection.create_connection = patched_create_connection

# 1. Configuration des intentions
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# ⚙️ CONFIGURATION DES CLÉS (VERSION SÉCURISÉE)
# Les tokens secrets sont lus directement depuis le panneau "Environment" de Render
BRAWL_STARS_TOKEN = os.getenv("BRAWL_STARS_TOKEN")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PLAYER_TAG = "2R9LRGCCYR" 

# Fonction pour attribuer un groupe de tri selon tes critères de trophées
def determiner_groupe_tri(brawler_data):
    tr = brawler_data.get("trophies", 0)
    if tr < 250: return 1
    elif tr < 500: return 2
    elif tr < 750: return 3
    elif tr < 1000: return 4
    elif tr < 1050: return 5
    elif tr < 2000: return 6
    else: return 7

# 2. La commande Slash /csvstats
@bot.tree.command(name="csvstats", description="Génère le fichier CSV de mes brawlers triés par trophées")
async def csvstats(interaction: discord.Interaction):
    await interaction.response.defer()
    
    clean_tag = PLAYER_TAG.replace("#", "").strip().upper()
    url = f"https://api.brawlstars.com/v1/players/%23{clean_tag}"
    headers = {"Authorization": f"Bearer {BRAWL_STARS_TOKEN}"}
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            await interaction.followup.send(f"❌ Erreur API Brawl Stars (Code : {response.status_code}).")
            return
            
        data = response.json()
        player_name = data.get("name", "Joueur")
        total_trophies = data.get("trophies", 0)
        
        # Récupération de la liste brute des brawlers
        brawlers_list = data.get("brawlers", [])
        
        # TRI STRUCTURÉ : On trie d'abord par groupe de trophées, puis par trophées exacts
        brawlers_list.sort(key=lambda x: (determiner_groupe_tri(x), x.get("trophies", 0)))
        
        # 3. Création du fichier CSV
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        
        # Lignes d'en-tête avec ton total général
        writer.writerow(["Joueur", "Trophées Globaux"])
        writer.writerow([player_name, total_trophies])
        writer.writerow([]) # Ligne vide pour aérer
        
        # Tableau simple des brawlers
        writer.writerow(["Brawler", "Trophées", "Niveau de Pouvoir"])
        
        for brawler in brawlers_list:
            writer.writerow([
                brawler.get("name"),
                brawler.get("trophies"),
                brawler.get("power")
            ])
            
        csv_buffer.seek(0)
        
        discord_file = discord.File(
            fp=io.BytesIO(csv_buffer.getvalue().encode('utf-8')), 
            filename=f"stats_{player_name}.csv"
        )
        
        await interaction.followup.send(content=f"📊 Fichier CSV généré pour **{player_name}** !", file=discord_file)

    except Exception as e:
        await interaction.followup.send(f"⚠️ Une erreur est survenue : {str(e)}")

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user.name}")
    
    # 📡 SCRIPT TEMPORAIRE POUR RÉCUPÉRER L'IP DE RENDER
    try:
        ip_detectee = requests.get('https://api.ipify.org', timeout=5).text
        print(f"📡 📡 📡 MON IP RENDER EST : {ip_detectee} 📡 📡 📡")
    except Exception as e:
        print(f"Impossible de récupérer l'IP automatiquement : {e}")

    try:
        synced = await bot.tree.sync()
        print(f"🔗 {len(synced)} commande(s) slash synchronisée(s).")
    except Exception as e:
        print(f"Erreur de synchronisation : {e}")

# Lancement sécurisé
bot.run(DISCORD_BOT_TOKEN)
