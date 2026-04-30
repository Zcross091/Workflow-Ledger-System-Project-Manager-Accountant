import discord
from discord import app_commands, ui
import sqlite3
import os
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
# This is your unique ID (Yahya) for "Super Admin" actions like clearing the whole database
OWNER_ID = 930518448268804096 

# --- DATABASE LAYER ---
def init_db():
    conn = sqlite3.connect('business_ledger.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            client_name TEXT,
            title TEXT,
            details TEXT,
            deadline TEXT,
            base_pay REAL,
            units INTEGER DEFAULT 0,
            worker_name TEXT,
            worker_id INTEGER,
            message_id INTEGER,
            status TEXT DEFAULT 'OPEN',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# --- UI COMPONENTS ---
class ProjectForm(ui.Modal, title='Project Intake'):
    title_input = ui.TextInput(label='Project Title', placeholder='Video Edit, Scripting...')
    details = ui.TextInput(label='Requirements', style=discord.TextStyle.paragraph)
    deadline = ui.TextInput(label='Deadline', placeholder='e.g. Tomorrow 5PM')
    budget = ui.TextInput(label='Budget (₹)', placeholder='1000')

    async def on_submit(self, interaction: discord.Interaction):
        try:
            conn = sqlite3.connect('business_ledger.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO projects (guild_id, client_name, title, details, deadline, base_pay) 
                              VALUES (?, ?, ?, ?, ?, ?)''', 
                           (interaction.guild_id, interaction.user.name, self.title_input.value, 
                            self.details.value, self.deadline.value, float(self.budget.value)))
            t_id = cursor.lastrowid
            
            embed = discord.Embed(title=f"📋 JOB: #{t_id}", color=discord.Color.blue())
            embed.add_field(name="Project", value=self.title_input.value, inline=False)
            embed.add_field(name="Budget", value=f"₹{self.budget.value}", inline=True)
            embed.add_field(name="Details", value=self.details.value, inline=False)
            embed.set_footer(text="React with 👍 to claim.")

            # Sends to the same channel the command was used in
            msg = await interaction.channel.send(embed=embed)
            await msg.add_reaction("👍")
            
            cursor.execute('UPDATE projects SET message_id = ? WHERE ticket_id = ?', (msg.id, t_id))
            conn.commit()
            conn.close()
            await interaction.response.send_message(f"✅ Ticket #{t_id} is live.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class LedgerBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True 
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Global Sync: Makes commands available in ALL servers
        await self.tree.sync()

    async def on_ready(self):
        init_db()
        print(f'Bot Publicly Active: {self.user}')

    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id: return
        if str(payload.emoji) == "👍":
            conn = sqlite3.connect('business_ledger.db')
            cursor = conn.cursor()
            cursor.execute('SELECT ticket_id, status FROM projects WHERE message_id = ?', (payload.message_id,))
            res = cursor.fetchone()
            if res and res[1] == 'OPEN':
                cursor.execute('UPDATE projects SET status = "CLAIMED", worker_id = ?, worker_name = ? WHERE ticket_id = ?', 
                               (payload.user_id, payload.member.name, res[0]))
                conn.commit()
                channel = self.get_channel(payload.channel_id)
                await channel.send(f"💼 **#{res[0]}** claimed by {payload.member.mention}.")
            conn.close()

bot = LedgerBot()

# --- PUBLIC COMMANDS ---

@bot.tree.command(name="post_job", description="MANAGER: Create a new project ticket.")
@app_commands.checks.has_permissions(manage_messages=True)
async def post_job(interaction: discord.Interaction):
    """Requires 'Manage Messages' permission so any server admin can use it."""
    await interaction.response.send_modal(ProjectForm())

@bot.tree.command(name="approve_work", description="MANAGER: Finalize work and log units.")
@app_commands.checks.has_permissions(manage_messages=True)
async def approve_work(interaction: discord.Interaction, ticket_id: int, units: int):
    conn = sqlite3.connect('business_ledger.db')
    cursor = conn.cursor()
    # Filters by guild_id so admins only see THEIR server's data
    cursor.execute('UPDATE projects SET status = "APPROVED", units = ? WHERE ticket_id = ? AND guild_id = ?', 
                   (units, ticket_id, interaction.guild_id))
    
    if cursor.rowcount > 0:
        await interaction.response.send_message(f"✅ Ticket #{ticket_id} approved for payout.")
    else:
        await interaction.response.send_message("❌ Ticket not found in this server.", ephemeral=True)
    conn.commit()
    conn.close()

@bot.tree.command(name="payout_list", description="ADMIN: View outstanding debt in this server.")
@app_commands.checks.has_permissions(administrator=True)
async def payout_list(interaction: discord.Interaction):
    conn = sqlite3.connect('business_ledger.db')
    cursor = conn.cursor()
    cursor.execute("SELECT worker_name, SUM(units) FROM projects WHERE status = 'APPROVED' AND guild_id = ? GROUP BY worker_name", 
                   (interaction.guild_id,))
    rows = cursor.fetchall()
    
    embed = discord.Embed(title="💰 Unpaid Balances", color=discord.Color.gold())
    if not rows:
        embed.description = "Ledger is clean."
    else:
        for name, total in rows:
            embed.add_field(name=name, value=f"Total Owed: ₹{total}", inline=False)
    
    await interaction.response.send_message(embed=embed)
    conn.close()

@bot.tree.command(name="settle_server", description="ADMIN: Reset this server's ledger to zero.")
@app_commands.checks.has_permissions(administrator=True)
async def settle_server(interaction: discord.Interaction):
    conn = sqlite3.connect('business_ledger.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET status = 'PAID' WHERE status = 'APPROVED' AND guild_id = ?", (interaction.guild_id,))
    conn.commit()
    conn.close()
    await interaction.response.send_message("✅ Server ledger cleared.")

@bot.tree.command(name="system_status", description="DEVELOPER: Check bot health and total database size.")
async def system_status(interaction: discord.Interaction):
    """Only YOU (Yahya) can see the global bot health."""
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("🚫 Developer Only.", ephemeral=True)
    
    conn = sqlite3.connect('business_ledger.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM projects")
    total_jobs = cursor.fetchone()[0]
    conn.close()
    
    await interaction.response.send_message(f"🛡️ **System Status**: Online\n📊 **Total Jobs Tracked (Global)**: {total_jobs}", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
