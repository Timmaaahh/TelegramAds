import time
import schedule
import os
import platform
from telethon import TelegramClient, sync, errors
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.channels import GetFullChannelRequest
from getpass import getpass
from pyfiglet import Figlet
from colorama import init, Fore, Style
from tqdm import tqdm
import logging
import json
from rich.console import Console
from rich.prompt import Prompt
from rich.progress import track
import keyring
import re

# Init colorama
init()

# Setup logging
logging.basicConfig(filename='telegram_bot.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Rich console
console = Console()

# Configuratie bestand
config_file = 'config.json'

# Laden van configuratie
def load_config():
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

config = load_config()

# Opslaan van configuratie
def save_config():
    with open(config_file, 'w') as f:
        json.dump(config, f)

# Disclaimer
console.print("Dit script is alleen bedoeld voor educatieve doeleinden. Gebruik dit script alleen met toestemming van de betrokken partijen.", style="bold red")

# Banner
f = Figlet(font='slant')
console.print(f.renderText('Telegram Bot'), style="bold green")

# API gegevens ophalen of opslaan
def get_api_credentials():
    api_id = keyring.get_password('telegram_bot', 'api_id')
    api_hash = keyring.get_password('telegram_bot', 'api_hash')
    if not api_id or not api_hash:
        api_id = Prompt.ask("[cyan]Voer je API ID in[/cyan]")
        api_hash = Prompt.ask("[cyan]Voer je API hash in[/cyan]")
        keyring.set_password('telegram_bot', 'api_id', api_id)
        keyring.set_password('telegram_bot', 'api_hash', api_hash)
    return api_id, api_hash

api_id, api_hash = get_api_credentials()
phone_number = Prompt.ask("[cyan]Voer je telefoonnummer in (inclusief landcode)[/cyan]")

client = TelegramClient('session_name', api_id, api_hash)

async def main():
    await client.start(phone_number)
    if not await client.is_user_authorized():
        try:
            await client.send_code_request(phone_number)
            code = Prompt.ask("[yellow]Voer de verificatiecode in[/yellow]")
            await client.sign_in(phone_number, code)
        except SessionPasswordNeededError:
            password = getpass("Je account is beschermd met een wachtwoord. Voer je wachtwoord in: ")
            await client.sign_in(password=password)
    console.print(f"Ingelogd als: {(await client.get_me()).username}", style="bold green")

client.loop.run_until_complete(main())

# Variabelen voor instellingen
min_interval = 30  # Telegram limiet in seconden
interval = config.get('interval', min_interval)

# Functie om groep-ID op te halen uit URL
async def get_group_id_from_url(url):
    username = re.search(r't.me/([a-zA-Z0-9_]+)', url).group(1)
    group = await client.get_entity(username)
    full_group = await client(GetFullChannelRequest(channel=group))
    return full_group.chats[0].id

# Hoofdmenu en functies
def main_menu():
    menu_options = {
        "1": "Bericht sturen",
        "2": "Afbeelding sturen",
        "3": "Instellingen",
        "4": "Log weergeven",
        "5": "Status Dashboard",
        "6": "Afsluiten"
    }

    console.print("\nHoofdmenu", style="bold blue")
    for key, value in menu_options.items():
        console.print(f"{key}. {value}", style="bold yellow")

    choice = Prompt.ask("[cyan]Maak een keuze[/cyan]")
    
    if choice == "1":
        send_message()
    elif choice == "2":
        send_image()
    elif choice == "3":
        settings()
    elif choice == "4":
        show_log()
    elif choice == "5":
        status_dashboard()
    elif choice == "6":
        exit(0)
    else:
        console.print("[red]Ongeldige keuze, probeer opnieuw.[/red]")
        main_menu()

def send_message():
    group_urls = Prompt.ask("[cyan]Voer de groeps-URL's in, gescheiden door een komma[/cyan]").split(',')
    message = Prompt.ask("[cyan]Voer het bericht in dat je wilt sturen[/cyan]")
    interval = Prompt.ask("[cyan]Voer het interval in seconden in (minimum 30 seconden)[/cyan]", default=str(min_interval))
    
    try:
        interval = int(interval)
        if interval < min_interval:
            console.print(f"[red]Interval moet minimaal {min_interval} seconden zijn.[/red]")
            return send_message()
    except ValueError:
        console.print("[red]Ongeldige invoer, probeer opnieuw.[/red]")
        return send_message()

    async def job():
        for url in track(group_urls, description="Berichten versturen"):
            try:
                group_id = await get_group_id_from_url(url.strip())
                await client.send_message(int(group_id), message)
                console.print(f"Bericht gestuurd naar groep {url}", style="bold green")
                logging.info(f"Bericht gestuurd naar groep {url}")
            except Exception as e:
                console.print(f"Fout bij het sturen naar groep {url}: {e}", style="bold red")
                logging.error(f"Fout bij het sturen naar groep {url}: {e}")

    schedule.every(interval).seconds.do(lambda: client.loop.run_until_complete(job()))
    while True:
        schedule.run_pending()
        time.sleep(1)

def send_image():
    group_urls = Prompt.ask("[cyan]Voer de groeps-URL's in, gescheiden door een komma[/cyan]").split(',')
    image_path = Prompt.ask("[cyan]Voer het pad naar de afbeelding in[/cyan]")
    caption = Prompt.ask("[cyan]Voer de bijschrift voor de afbeelding in[/cyan]")
    interval = Prompt.ask("[cyan]Voer het interval in seconden in (minimum 30 seconden)[/cyan]", default=str(min_interval))
    
    try:
        interval = int(interval)
        if interval < min_interval:
            console.print(f"[red]Interval moet minimaal {min_interval} seconden zijn.[/red]")
            return send_image()
    except ValueError:
        console.print("[red]Ongeldige invoer, probeer opnieuw.[/red]")
        return send_image()

    async def job():
        for url in track(group_urls, description="Afbeeldingen versturen"):
            try:
                group_id = await get_group_id_from_url(url.strip())
                await client.send_file(int(group_id), image_path, caption=caption)
                console.print(f"Afbeelding gestuurd naar groep {url}", style="bold green")
                logging.info(f"Afbeelding gestuurd naar groep {url}")
            except Exception as e:
                console.print(f"Fout bij het sturen naar groep {url}: {e}", style="bold red")
                logging.error(f"Fout bij het sturen naar groep {url}: {e}")

    schedule.every(interval).seconds.do(lambda: client.loop.run_until_complete(job()))
    while True:
        schedule.run_pending()
        time.sleep(1)

def settings():
    global interval
    console.print("[blue]Instellingen[/blue]")
    console.print(f"[yellow]Huidig interval: {interval} seconden[/yellow]")
    new_interval = Prompt.ask(f"[cyan]Voer nieuw interval in seconden in (minimum {min_interval} seconden)[/cyan]", default=str(interval))
    
    try:
        new_interval = int(new_interval)
        if new_interval < min_interval:
            console.print(f"[red]Interval moet minimaal {min_interval} seconden zijn.[/red]")
        else:
            interval = new_interval
            config['interval'] = interval
            save_config()
            console.print(f"[green]Interval ingesteld op {interval} seconden.[/green]")
            logging.info(f"Interval ingesteld op {interval} seconden")
    except ValueError:
        console.print("[red]Ongeldige invoer, probeer opnieuw.[/red]")
    
    main_menu()

def show_log():
    if os.path.exists('telegram_bot.log'):
        with open('telegram_bot.log', 'r') as file:
            for line in file:
                console.print(line.strip())
    else:
        console.print("[red]Geen logbestand gevonden.[/red]")
    Prompt.ask("[cyan]\nDruk op Enter om terug te keren naar het hoofdmenu.[/cyan]")
    main_menu()

def status_dashboard():
    console.print("[blue]Status Dashboard[/blue]")
    # Display some statistics and status
    console.print(f"[yellow]Ingelogd als: {(client.get_me()).username}[/yellow]")
    console.print(f"[yellow]Interval: {interval} seconden[/yellow]")
    console.print(f"[yellow]Geplande taken: {len(schedule.jobs)}[/yellow]")
    for job in schedule.jobs:
        console.print(f"[green]{job}[/green]")
    Prompt.ask("[cyan]\nDruk op Enter om terug te keren naar het hoofdmenu.[/cyan]")
    main_menu()

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("[red]\nScript beëindigd door gebruiker.[/red]")

