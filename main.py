
import discord
from discord.ext import commands
import asyncio
import random
import json
import os
from datetime import datetime, timedelta
from replit import db
from keep_alive import keep_alive

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def get_user_profile(user_id):
    user_id = str(user_id)
    
    # Try to get user data from Replit DB
    try:
        user_data = db.get(f"user_{user_id}")
        if user_data:
            return json.loads(user_data)
    except:
        pass
    
    # Create new user profile if doesn't exist
    new_profile = {
        'money': 0,
        'job': 'Homeless',
        'level': 1,
        'experience': 0,
        'last_work': None,
        'last_crime': None,
        'last_daily': None,
        'inventory': {},
        'achievements': [],
        'created_at': datetime.now().isoformat(),
        'premium': False,
        'premium_expires': None,
        'premium_features_used': {}
    }
    
    # Save to database
    save_user_profile(user_id, new_profile)
    return new_profile

def save_user_profile(user_id, profile):
    """Save user profile to Replit Key-Value Store"""
    user_id = str(user_id)
    try:
        db[f"user_{user_id}"] = json.dumps(profile)
        return True
    except Exception as e:
        print(f"Error saving user profile: {e}")
        return False

def get_all_users():
    """Get all user profiles for leaderboard"""
    users = {}
    try:
        # Get all keys that start with "user_"
        keys = db.prefix("user_")
        for key in keys:
            user_id = key.replace("user_", "")
            try:
                profile = json.loads(db[key])
                users[user_id] = profile
            except:
                continue
    except:
        pass
    return users

def get_level_requirements(level):
    return level * 100

def check_level_up(profile):
    required_exp = get_level_requirements(profile['level'])
    if profile['experience'] >= required_exp:
        profile['level'] += 1
        profile['experience'] = 0
        return True
    return False

def get_status_from_money(money):
    if money < 100:
        return "💸 Broke"
    elif money < 1000:
        return "💰 Getting Started"
    elif money < 10000:
        return "💵 Middle Class"
    elif money < 100000:
        return "💎 Rich"
    elif money < 1000000:
        return "👑 Very Rich"
    else:
        return "🏰 Millionaire"

def is_premium(profile):
    """Check if user has active premium"""
    if not profile.get('premium', False):
        return False
    
    if profile.get('premium_expires'):
        expiry = datetime.fromisoformat(profile['premium_expires'])
        if datetime.now() > expiry:
            # Premium expired
            profile['premium'] = False
            profile['premium_expires'] = None
            return False
    
    return True

def format_premium_status(profile):
    """Get premium status string"""
    if is_premium(profile):
        if profile.get('premium_expires'):
            expiry = datetime.fromisoformat(profile['premium_expires'])
            return f"👑 Premium (expires {expiry.strftime('%b %d, %Y')})"
        else:
            return "👑 Premium (lifetime)"
    return "🆓 Free"

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')
    print('Poor to Rich Simulator Bot is ready!')
    print('Using Replit Key-Value Store for data persistence!')

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors and provide helpful suggestions"""
    if isinstance(error, discord.ext.commands.MissingRequiredArgument):
        # Get the command name that was attempted
        command_name = ctx.command.name if ctx.command else "unknown"
        
        # Dictionary of command help messages
        command_help = {
            'deal': {
                'usage': '!deal @user <amount> <days>',
                'description': 'Give a loan to another player',
                'example': '!deal @JohnDoe 5000 7',
                'explanation': '• @user: The person to give the loan to\n• amount: Money amount (max $50,000)\n• days: Loan duration (max 30 days)\n\n⚠️ If loan isn\'t repaid, borrower loses everything!'
            },
            'gift': {
                'usage': '!gift @user <amount>',
                'description': 'Gift money to another player',
                'example': '!gift @JohnDoe 1000',
                'explanation': '• @user: The person to gift money to\n• amount: How much money to give'
            },
            'buy': {
                'usage': '!buy <item_name>',
                'description': 'Buy an item from the shop',
                'example': '!buy phone',
                'explanation': '• item_name: phone, laptop, car, house, or watch\nUse !shop to see all available items'
            },
            'rob': {
                'usage': '!rob @user',
                'description': 'Attempt to rob another player',
                'example': '!rob @JohnDoe',
                'explanation': '• @user: The player to attempt robbing\n• Target must have at least $100\n• 1 hour cooldown between attempts'
            },
            'gamble': {
                'usage': '!gamble <amount>',
                'description': 'Risk money for potential rewards',
                'example': '!gamble 500',
                'explanation': '• amount: How much money to risk\n• Higher risk = higher potential reward'
            },
            'invest': {
                'usage': '!invest <stock> <shares>',
                'description': 'Buy stocks for potential profit',
                'example': '!invest TECH 10',
                'explanation': '• stock: TECH, FOOD, AUTO, GAME, or BANK\n• shares: Number of shares to buy\nUse !stocks to see current prices'
            },
            'addmoney': {
                'usage': '!addmoney @user <amount>',
                'description': '[OWNER ONLY] Add unlimited money',
                'example': '!addmoney @JohnDoe 1000000',
                'explanation': '• @user: Player to give money to (optional)\n• amount: Amount to add (optional, default 1M)'
            },
            'setmoney': {
                'usage': '!setmoney @user <amount>',
                'description': '[OWNER ONLY] Set exact money amount',
                'example': '!setmoney @JohnDoe 50000',
                'explanation': '• @user: Player to set money for\n• amount: Exact amount to set'
            },
            'buypremium': {
                'usage': '!buypremium <plan>',
                'description': 'Purchase premium access',
                'example': '!buypremium month',
                'explanation': '• plan: week ($10K), month ($35K), or lifetime ($100K)\nUse !premium to see all benefits'
            },
            'vault': {
                'usage': '!vault <action> <amount>',
                'description': '[PREMIUM] Secure money storage',
                'example': '!vault deposit 5000',
                'explanation': '• action: deposit or withdraw\n• amount: How much money to move\nVault protects money from robberies!'
            },
            'premiumgift': {
                'usage': '!premiumgift @user <amount> <message>',
                'description': '[PREMIUM] Send stylish gifts',
                'example': '!premiumgift @JohnDoe 1000 Happy birthday!',
                'explanation': '• @user: Person to gift to\n• amount: Money amount\n• message: Personal message (optional)'
            },
            'premiumcasino': {
                'usage': '!premiumcasino <amount>',
                'description': '[PREMIUM] High-stakes gambling',
                'example': '!premiumcasino 5000',
                'explanation': '• amount: Money to bet (minimum $1,000)\nBetter odds than regular gambling!'
            }
        }
        
        if command_name in command_help:
            cmd_info = command_help[command_name]
            embed = discord.Embed(
                title=f"❓ Command Help: {cmd_info['usage']}",
                description=cmd_info['description'],
                color=0x3498db
            )
            embed.add_field(name="📖 Usage", value=f"`{cmd_info['usage']}`", inline=False)
            embed.add_field(name="💡 Example", value=f"`{cmd_info['example']}`", inline=False)
            embed.add_field(name="📋 Parameters", value=cmd_info['explanation'], inline=False)
            embed.set_footer(text="💡 Tip: Use !start to see all basic commands!")
            
            await ctx.send(embed=embed)
        else:
            # Generic missing argument message
            await ctx.send(f"❌ Missing required arguments for `!{command_name}`!\nUse `!start` to see all available commands.")
    
    elif isinstance(error, discord.ext.commands.CommandNotFound):
        # Handle unknown commands by suggesting similar ones
        attempted_command = ctx.message.content.split()[0][1:]  # Remove the ! prefix
        
        # Dictionary of common command suggestions
        suggestions = {
            'prem': ['premium', 'premiumstatus', 'premiumdaily'],
            'premium': ['premium', 'premiumstatus', 'buypremium'],
            'money': ['addmoney', 'setmoney', 'work'],
            'help': ['start', 'guide', 'emergency'],
            'loan': ['deal', 'repay', 'loans'],
            'steal': ['rob', 'crime', 'heist'],
            'bet': ['gamble', 'premiumcasino'],
            'stock': ['stocks', 'invest'],
            'shop': ['shop', 'buy'],
            'daily': ['daily', 'premiumdaily'],
            'vault': ['vault'] if attempted_command.startswith('vault') else ['profile'],
            'casino': ['gamble', 'premiumcasino'],
            'heist': ['heist', 'premiumheist']
        }
        
        # Find suggestions based on partial matches
        suggested_commands = []
        for key, commands in suggestions.items():
            if key in attempted_command.lower() or attempted_command.lower() in key:
                suggested_commands.extend(commands)
        
        if suggested_commands:
            embed = discord.Embed(
                title="❓ Command Not Found",
                description=f"Command `!{attempted_command}` not found. Did you mean:",
                color=0xf39c12
            )
            
            # Remove duplicates and limit to 5 suggestions
            unique_suggestions = list(set(suggested_commands))[:5]
            suggestions_text = '\n'.join([f"`!{cmd}`" for cmd in unique_suggestions])
            
            embed.add_field(name="💡 Suggestions", value=suggestions_text, inline=False)
            embed.add_field(name="📚 Need Help?", value="Use `!start` to see all commands\nUse `!guide` for AI assistance", inline=False)
            
            await ctx.send(embed=embed)
        else:
            # No specific suggestions found
            embed = discord.Embed(
                title="❓ Command Not Found",
                description=f"Command `!{attempted_command}` doesn't exist.",
                color=0xe74c3c
            )
            embed.add_field(name="📚 Available Commands", value="Use `!start` to see all commands\nUse `!guide` for AI assistance", inline=False)
            
            await ctx.send(embed=embed)
    
    else:
        # Handle other types of errors
        await ctx.send(f"❌ An error occurred: {str(error)}")
        print(f"Command error: {error}")

@bot.command(name='start')
async def start_game(ctx):
    """Start your journey from poor to rich!"""
    profile = get_user_profile(ctx.author.id)
    
    embed = discord.Embed(
        title="🎮 Welcome to Poor to Rich Simulator!",
        description=f"Welcome {ctx.author.mention}! Your journey begins...",
        color=0x00ff00
    )
    
    embed.add_field(name="💰 Money", value=f"${profile['money']}", inline=True)
    embed.add_field(name="👔 Job", value=profile['job'], inline=True)
    embed.add_field(name="📊 Level", value=f"{profile['level']}", inline=True)
    embed.add_field(name="🏆 Status", value=get_status_from_money(profile['money']), inline=True)
    
    embed.add_field(
        name="📋 Basic Commands",
        value="`!work` - Work for money\n`!crime` - Risk it for money\n`!profile` - View your stats\n`!shop` - Buy items\n`!leaderboard` - Top players\n`!daily` - Daily bonus\n`!gift @user amount` - Gift money to someone",
        inline=False
    )
    
    embed.add_field(
        name="🎰 Advanced Features",
        value="`!gamble <amount>` - High risk gambling\n`!rob @user` - Rob other players\n`!stocks` - View stock market\n`!invest <stock> <shares>` - Buy stocks\n`!heist` - Start group heist\n`!achievements` - View achievements",
        inline=False
    )
    
    embed.add_field(
        name="😈 Sukuna's Commands (Owner Only)",
        value="`!addmoney @user amount` - Add unlimited money\n`!setmoney @user amount` - Set exact money amount",
        inline=False
    )
    
    embed.set_footer(text="💾 Your progress is automatically saved!")
    
    await ctx.send(embed=embed)

@bot.command(name='profile')
async def show_profile(ctx, member: discord.Member = None):
    """Show your or someone else's profile"""
    target = member or ctx.author
    profile = get_user_profile(target.id)
    
    embed = discord.Embed(
        title=f"👤 {target.display_name}'s Profile",
        color=0x3498db
    )
    
    embed.add_field(name="💰 Money", value=f"${profile['money']:,}", inline=True)
    embed.add_field(name="👔 Job", value=profile['job'], inline=True)
    embed.add_field(name="📊 Level", value=f"{profile['level']}", inline=True)
    embed.add_field(name="⭐ Experience", value=f"{profile['experience']}/{get_level_requirements(profile['level'])}", inline=True)
    embed.add_field(name="🏆 Status", value=get_status_from_money(profile['money']), inline=True)
    embed.add_field(name="👑 Premium", value=format_premium_status(profile), inline=True)
    
    # Show account creation date
    if 'created_at' in profile:
        created = datetime.fromisoformat(profile['created_at'])
        embed.add_field(name="📅 Joined", value=created.strftime("%B %d, %Y"), inline=True)
    
    if profile['achievements']:
        embed.add_field(name="🏅 Achievements", value='\n'.join(profile['achievements'][:5]), inline=False)
    
    if profile['inventory']:
        items = [item.replace('_', ' ').title() for item in profile['inventory'].keys()]
        embed.add_field(name="🎒 Inventory", value=', '.join(items[:5]), inline=False)
    
    embed.set_footer(text="💾 Data saved in Replit Database")
    
    await ctx.send(embed=embed)

@bot.command(name='work')
async def work(ctx):
    """Work to earn money"""
    profile = get_user_profile(ctx.author.id)
    
    # Check cooldown
    if profile['last_work']:
        last_work = datetime.fromisoformat(profile['last_work'])
        cooldown_minutes = 5
        
        # Car reduces cooldown
        if 'car' in profile['inventory']:
            cooldown_minutes = 3
        
        # Premium reduces cooldown by 50%
        if is_premium(profile):
            cooldown_minutes = int(cooldown_minutes * 0.5)
            
        if datetime.now() - last_work < timedelta(minutes=cooldown_minutes):
            remaining = timedelta(minutes=cooldown_minutes) - (datetime.now() - last_work)
            await ctx.send(f"⏰ You need to wait {remaining.seconds//60}m {remaining.seconds%60}s before working again!")
            return
    
    # Work earnings based on level and job
    base_earnings = random.randint(10, 50)
    level_bonus = profile['level'] * 5
    earnings = base_earnings + level_bonus
    
    # Job multiplier
    job_multipliers = {
        'Homeless': 0.5,
        'Street Cleaner': 1.0,
        'Cashier': 1.5,
        'Office Worker': 2.0,
        'Manager': 3.0,
        'CEO': 5.0
    }
    
    multiplier = job_multipliers.get(profile['job'], 1.0)
    
    # Item bonuses
    if 'phone' in profile['inventory']:
        multiplier *= 1.1  # 10% bonus
    if 'laptop' in profile['inventory']:
        multiplier *= 1.25  # 25% bonus
    
    # Premium bonuses
    if is_premium(profile):
        if profile.get('premium_expires'):
            # Monthly/weekly premium
            multiplier *= 3.0  # 3x earnings
        else:
            # Lifetime premium
            multiplier *= 5.0  # 5x earnings
    
    final_earnings = int(earnings * multiplier)
    exp_gained = random.randint(5, 15)
    
    profile['money'] += final_earnings
    profile['experience'] += exp_gained
    profile['last_work'] = datetime.now().isoformat()
    
    # Check for level up
    leveled_up = check_level_up(profile)
    
    # Job promotions based on money
    old_job = profile['job']
    if profile['money'] >= 1000 and profile['job'] == 'Homeless':
        profile['job'] = 'Street Cleaner'
    elif profile['money'] >= 5000 and profile['job'] == 'Street Cleaner':
        profile['job'] = 'Cashier'
    elif profile['money'] >= 25000 and profile['job'] == 'Cashier':
        profile['job'] = 'Office Worker'
    elif profile['money'] >= 100000 and profile['job'] == 'Office Worker':
        profile['job'] = 'Manager'
    elif profile['money'] >= 500000 and profile['job'] == 'Manager':
        profile['job'] = 'CEO'
    
    # Save profile to database
    save_user_profile(ctx.author.id, profile)
    
    work_messages = [
        "You worked hard and earned some money!",
        "Another day, another dollar!",
        "Your hard work is paying off!",
        "You put in some honest work!",
        "Time is money, and you just made some!"
    ]
    
    embed = discord.Embed(
        title="💼 Work Complete!",
        description=random.choice(work_messages),
        color=0x2ecc71
    )
    
    embed.add_field(name="💰 Earned", value=f"${final_earnings}", inline=True)
    embed.add_field(name="💳 Total Money", value=f"${profile['money']:,}", inline=True)
    embed.add_field(name="⭐ XP Gained", value=f"+{exp_gained}", inline=True)
    
    if leveled_up:
        embed.add_field(name="📈 Level Up!", value=f"You reached level {profile['level']}!", inline=False)
    
    if old_job != profile['job']:
        embed.add_field(name="🎉 Promotion!", value=f"You got promoted to {profile['job']}!", inline=False)
    
    embed.set_footer(text="💾 Progress automatically saved!")
    
    await ctx.send(embed=embed)

@bot.command(name='crime')
async def commit_crime(ctx):
    """Risk money for a chance at big rewards"""
    profile = get_user_profile(ctx.author.id)
    
    # Check cooldown
    if profile['last_crime']:
        last_crime = datetime.fromisoformat(profile['last_crime'])
        if datetime.now() - last_crime < timedelta(minutes=10):
            remaining = timedelta(minutes=10) - (datetime.now() - last_crime)
            await ctx.send(f"🚔 You need to lay low for {remaining.seconds//60}m {remaining.seconds%60}s!")
            return
    
    success_rate = 0.6  # 60% success rate
    
    if random.random() < success_rate:
        # Success
        earnings = random.randint(50, 200) + (profile['level'] * 10)
        profile['money'] += earnings
        profile['experience'] += random.randint(10, 25)
        
        crimes = [
            "pickpocketed a wealthy businessman",
            "found a wallet on the street",
            "won a street game",
            "sold some questionable items",
            "completed a shady deal"
        ]
        
        embed = discord.Embed(
            title="😈 Crime Successful!",
            description=f"You {random.choice(crimes)} and got away with it!",
            color=0xe74c3c
        )
        embed.add_field(name="💰 Earned", value=f"${earnings}", inline=True)
        embed.add_field(name="💳 Total Money", value=f"${profile['money']:,}", inline=True)
        
    else:
        # Failure
        fine = min(profile['money'] // 4, 100)  # Lose up to 25% or $100, whichever is less
        profile['money'] 
keep_alive()
bot.run(os.getenv("TOKEN"))
