import json
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich import print
from datetime import datetime
import os
import time
import re
from rich.progress import Progress, SpinnerColumn, TextColumn
from urllib.parse import urlparse
import subprocess

console = Console()

GITHUB_RAW_URL = "https://raw.githubusercontent.com/bonkerd/bonkerd.github.io/refs/heads/main/games.json"
DOWNLOADS_DIR = "downloads"

def get_store_name(url):
    domain = urlparse(url).netloc.lower()
    if 'steampowered.com' in domain:
        return 'Steam'
    elif 'epicgames.com' in domain:
        return 'Epic Games'
    elif 'gog.com' in domain:
        return 'GOG'
    else:
        return 'Unknown Store'

def get_host_name(url):
    domain = urlparse(url).netloc.lower()
    
    # Common file hosting services
    host_mapping = {
        'drive.google.com': 'Google Drive',
        'mega.nz': 'Mega',
        'mediafire.com': 'MediaFire',
        'dropbox.com': 'Dropbox',
        'onedrive.live.com': 'OneDrive',
        'files.fm': 'Files.fm',
        '1fichier.com': '1Fichier',
        'uploaded.net': 'Uploaded',
        'zippyshare.com': 'ZippyShare',
        'sendspace.com': 'SendSpace',
        'rapidgator.net': 'RapidGator',
        'uptobox.com': 'UptoBox',
        'pixeldrain.com': 'PixelDrain',
        'gofile.io': 'GoFile',
        'anonfiles.com': 'AnonFiles'
    }
    
    # Try to match the domain with known hosts
    for host_domain, host_name in host_mapping.items():
        if host_domain in domain:
            return host_name
    
    # If no match found, return the domain name in a clean format
    clean_domain = domain.replace('www.', '').split('.')[0].title()
    return clean_domain

def extract_size_from_requirements(requirements_text):
    if not requirements_text:
        return "Unknown size"
    
    # Try to find size in the format "XX GB available space"
    size_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:GB|MB) (?:available )?space', requirements_text, re.IGNORECASE)
    if size_match:
        size = size_match.group(1)
        unit = 'GB' if 'GB' in requirements_text else 'MB'
        return f"{size} {unit}"
    return "Unknown size"

def get_game_info(app_id):
    try:
        response = requests.get(f"https://store.steampowered.com/api/appdetails?appids={app_id}")
        data = response.json()
        if data and data.get(str(app_id), {}).get('success'):
            game_data = data[str(app_id)]['data']
            return {
                'description': game_data.get('short_description', 'No description available'),
                'size': extract_size_from_requirements(game_data.get('pc_requirements', {}).get('minimum', ''))
            }
        return {'description': 'No description available', 'size': 'Unknown size'}
    except Exception as e:
        return {'description': f'Error fetching info: {e}', 'size': 'Unknown size'}

def load_games_data():
    # First try to load local file
    local_path = 'games.json'
    try:
        if os.path.exists(local_path):
            console.print("[cyan]Using local games.json file...[/cyan]")
            with open(local_path, 'r') as f:
                return json.load(f)
        
        # If local file doesn't exist, try online
        console.print("[cyan]Local games.json not found, fetching from GitHub...[/cyan]")
        response = requests.get(GITHUB_RAW_URL)
        if response.status_code == 200:
            # Save a local copy for future use
            data = response.json()
            try:
                with open(local_path, 'w') as f:
                    json.dump(data, f, indent=2)
                console.print("[green]Created local copy of games.json[/green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not save local copy: {e}[/yellow]")
            return data
        else:
            console.print(f"[red]Error fetching games data: HTTP {response.status_code}[/red]")
            return None
    except requests.exceptions.ConnectionError:
        console.print("[red]Error: Could not connect to GitHub. Check your internet connection.[/red]")
        # If we have a local file but couldn't connect, try to use it as fallback
        if os.path.exists(local_path):
            console.print("[yellow]Attempting to use existing local file as fallback...[/yellow]")
            try:
                with open(local_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                console.print(f"[red]Error reading local file: {e}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]Error loading games data: {e}[/red]")
        return None

def get_installed_browsers():
    """Get a list of installed browsers on Windows"""
    common_browsers = {
        'chrome': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        'chrome_x86': r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        'firefox': r'C:\Program Files\Mozilla Firefox\firefox.exe',
        'firefox_x86': r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe',
        'edge': r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        'opera': r'C:\Program Files\Opera\launcher.exe',
        'opera_x86': r'C:\Program Files (x86)\Opera\launcher.exe',
        'brave': r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe',
    }
    
    installed = {}
    for name, path in common_browsers.items():
        if os.path.exists(path):
            # Clean up the name (remove _x86 suffix and capitalize)
            clean_name = name.split('_')[0].capitalize()
            installed[clean_name] = path
    
    return installed

def open_in_browser(url, browser_path=None):
    """Open URL in specified browser or show browser selection"""
    if not browser_path:
        browsers = get_installed_browsers()
        if not browsers:
            console.print("[red]No supported browsers found. Opening in default browser...[/red]")
            subprocess.run(['start', url], shell=True)
            return
        
        # Show browser options
        console.print("\n[yellow]Available Browsers:[/yellow]")
        browser_list = list(browsers.keys())
        for i, browser in enumerate(browser_list, 1):
            print(f"[yellow]{i}.[/yellow] {browser}")
        print(f"[yellow]{len(browser_list) + 1}.[/yellow] Default Browser")
        
        choice = Prompt.ask(
            "Select browser",
            choices=[str(i) for i in range(1, len(browser_list) + 2)],
            show_choices=False
        )
        
        choice = int(choice)
        if choice == len(browser_list) + 1:
            subprocess.run(['start', url], shell=True)
        else:
            selected_browser = browser_list[choice - 1]
            subprocess.Popen([browsers[selected_browser], url])
    else:
        subprocess.Popen([browser_path, url])

def open_store_page(url):
    """Open store page in browser"""
    open_in_browser(url)

def download_game(game):
    if not game['downloads']:
        console.print("[red]No download links available for this game.[/red]")
        return

    console.clear()
    # Create downloads directory if it doesn't exist
    if not os.path.exists(DOWNLOADS_DIR):
        os.makedirs(DOWNLOADS_DIR)
    
    # Get game size from store API
    game_info = get_game_info(game['app_id'])
    
    # Show available download sources
    console.print(Panel.fit(
        f"[bold cyan]Download Options for {game['title']}[/bold cyan]",
        border_style="magenta"
    ))
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Host", style="green")
    table.add_column("Size", style="yellow")
    
    for i, download in enumerate(game['downloads'], 1):
        host_name = get_host_name(download['url'])
        table.add_row(str(i), host_name, game_info['size'])
    
    console.print(table)
    
    # Ask user to choose a download source
    choice = Prompt.ask("\nSelect download source (or press Enter to cancel)", default="")
    
    if choice.isdigit() and 1 <= int(choice) <= len(game['downloads']):
        download = game['downloads'][int(choice)-1]
        host_name = get_host_name(download['url'])
        
        console.clear()
        # Show download progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(f"Opening download link for {game['title']} from {host_name}...", total=None)
            time.sleep(1)
        
        # Open download URL in browser
        open_store_page(download['url'])
        console.print(f"\n[green]Download link opened in your browser![/green]")
        time.sleep(2)
    
    game_path = os.path.join(DOWNLOADS_DIR, f"{game['title']}.game")
    with open(game_path, 'w') as f:
        json.dump(game, f, indent=2)

def get_version_info(game):
    """Get version information with fallback to default values"""
    if 'versions' in game and game['versions']:
        latest = game['versions'][-1]
        return {
            'version': latest.get('version', 'N/A'),
            'date': datetime.strptime(latest.get('date', '2000-01-01T00:00:00Z'), '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M'),
            'changes': latest.get('changes', 'No change information')
        }
    return {
        'version': 'N/A',
        'date': 'N/A',
        'changes': 'No version information available'
    }

def display_game_list(games, sort_by_date=False):
    while True:
        console.clear()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Title", style="cyan")
        table.add_column("Latest Version", style="green")
        table.add_column("Last Updated", style="yellow")
        
        game_list = games['games']
        if sort_by_date:
            # Only sort by date if version information is available
            game_list = sorted(
                game_list,
                key=lambda x: datetime.strptime(
                    x.get('versions', [{'date': '2000-01-01T00:00:00Z'}])[-1].get('date', '2000-01-01T00:00:00Z'),
                    '%Y-%m-%dT%H:%M:%SZ'
                ),
                reverse=True
            )
        else:
            game_list = sorted(game_list, key=lambda x: x['title'])
        
        console.print(Panel.fit(
            "[bold cyan]Game Library[/bold cyan]",
            border_style="magenta"
        ))
        
        for i, game in enumerate(game_list, 1):
            version_info = get_version_info(game)
            table.add_row(
                str(i),
                game['title'],
                version_info['version'],
                version_info['date']
            )
        
        console.print(table)
        console.print("\n[yellow]Options:[/yellow]")
        print("[yellow]1-" + str(len(game_list)) + ".[/yellow] Select Game")
        print("[yellow]B.[/yellow] Back to Main Menu")
        
        choice = Prompt.ask("Select an option", default="").upper()
        
        if choice == "B":
            return
        elif choice.isdigit() and 1 <= int(choice) <= len(game_list):
            if display_game_details(game_list[int(choice)-1]):
                continue  # Stay in game list if returning from details
            else:
                return  # Exit to main menu if user chose to exit

def display_game_details(game):
    while True:
        console.clear()
        game_info = get_game_info(game['app_id'])
        store_name = get_store_name(game['store_url'])
        version_info = get_version_info(game)
        
        # Display game info
        version_text = f"[yellow]Latest Version:[/yellow] {version_info['version']}\n" if version_info['version'] != 'N/A' else ""
        update_text = f"[yellow]Last Updated:[/yellow] {version_info['date']}\n" if version_info['date'] != 'N/A' else ""
        
        console.print(Panel.fit(
            f"[bold cyan]{game['title']}[/bold cyan]\n\n"
            f"[yellow]Description:[/yellow]\n{game_info['description']}\n\n"
            f"[yellow]Store:[/yellow] {store_name}\n"
            f"[yellow]Size:[/yellow] {game_info['size']}\n"
            f"{version_text}"
            f"{update_text}",
            border_style="magenta"
        ))
        
        # Display options
        console.print("\n[yellow]Options:[/yellow]")
        print("[yellow]1.[/yellow] Visit Store Page")
        print("[yellow]2.[/yellow] Download Game")
        print("[yellow]3.[/yellow] Back to Game List")
        print("[yellow]4.[/yellow] Exit to Main Menu")
        
        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4"], show_choices=False)
        
        if choice == "1":
            open_store_page(game['store_url'])
            console.print(f"\n[green]Opening {store_name} store page...[/green]")
            time.sleep(1)
        elif choice == "2":
            download_game(game)
            time.sleep(1)
        elif choice == "3":
            return True  # Return to game list
        elif choice == "4":
            return False  # Exit to main menu

def search_games(games, query):
    while True:
        console.clear()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Title", style="cyan")
        table.add_column("Latest Version", style="yellow")
        
        matching_games = []
        for game in games['games']:
            if query.lower() in game['title'].lower():
                matching_games.append(game)
        
        if matching_games:
            console.print(Panel.fit(
                f"[bold cyan]Search Results for '{query}'[/bold cyan]",
                border_style="magenta"
            ))
            
            for i, game in enumerate(matching_games, 1):
                version_info = get_version_info(game)
                table.add_row(
                    str(i),
                    game['title'],
                    version_info['version']
                )
            
            console.print(table)
            console.print("\n[yellow]Options:[/yellow]")
            print("[yellow]1-" + str(len(matching_games)) + ".[/yellow] Select Game")
            print("[yellow]B.[/yellow] Back to Main Menu")
            
            choice = Prompt.ask("Select an option", default="").upper()
            
            if choice == "B":
                return
            elif choice.isdigit() and 1 <= int(choice) <= len(matching_games):
                if display_game_details(matching_games[int(choice)-1]):
                    continue  # Stay in search results if returning from details
                else:
                    return  # Exit to main menu if user chose to exit
        else:
            console.print(Panel.fit(
                f"[red]No games found matching '{query}'[/red]",
                border_style="magenta"
            ))
            time.sleep(2)
            return

def main_menu():
    while True:
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]Game Downloader[/bold cyan]",
            border_style="magenta"
        ))
        
        console.print("\n[yellow]Options:[/yellow]")
        print("[yellow]1.[/yellow] View All Games (A-Z)")
        print("[yellow]2.[/yellow] View Latest Updated Games")
        print("[yellow]3.[/yellow] Search Games")
        print("[yellow]4.[/yellow] Exit")
        
        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4"], show_choices=False)
        
        games_data = load_games_data()
        if not games_data:
            time.sleep(2)
            continue
        
        if choice == "1":
            display_game_list(games_data)
        elif choice == "2":
            display_game_list(games_data, sort_by_date=True)
        elif choice == "3":
            console.clear()
            query = Prompt.ask("Enter search term")
            search_games(games_data, query)
        elif choice == "4":
            console.clear()
            console.print("\n[cyan]Thanks for using Game Downloader![/cyan]")
            break

if __name__ == "__main__":
    main_menu()
