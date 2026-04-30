import discord
from discord import app_commands, ui
import sqlite3
import os
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
WORKER_CHANNEL_ID = 1497993985837498402 
ADMIN_ID = 930518448268804096          

# --- DATABASE LAYER ---
def init_db():
    conn = sqlite3.connect('business_ledger.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
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

# --- PROFESSIONAL UI COMPONENTS ---
class ProjectForm(ui.Modal, title='New Project Intake'):
    title = ui.TextInput(label='Project Title', placeholder='e.g. YouTube Edit, 5x Thumbnails...')
    details = ui.TextInput(label='Requirements & Links', style=discord.TextStyle.paragraph, placeholder='Instructions for the worker...')
    deadline = ui.TextInput(label='Hard Deadline', placeholder='e.g. Friday 6PM IST')
    budget = ui.TextInput(label='Base Budget (₹)', placeholder='e.g. 1500')

    async def on_submit(self, interaction: discord.Interaction):
        try:
            conn = sqlite3.connect('business_ledger.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO projects (client_name, title, details, deadline, base_pay) 
                              VALUES (?, ?, ?, ?, ?)''', 
                           (interaction.user.name, self.title.value, self.details.value, self.deadline.value, float(self.budget.value)))
            t_id = cursor.lastrowid
            
            embed = discord.Embed(title=f"📋 NEW JOB: #{t_id}", color=discord.Color.blue())
            embed.add_field(name="Project", value=self.title.value, inline=False)
            embed.add_field(name="Deadline", value=self.deadline.value, inline=True)
            embed.add_field(name="Budget", value=f"₹{self.budget.value}", inline=True)
            embed.add_field(name="Details", value=self.details.value, inline=False)
            embed.set_footer(text="WORKERS: React with 👍 to lock this project to your name.")

            channel = interaction.guild.get_channel(WORKER_CHANNEL_ID)
            if channel:
                msg = await channel.send(embed=embed)
                await msg.add_reaction("👍")
                cursor.execute('UPDATE projects SET message_id = ? WHERE ticket_id = ?', (msg.id, t_id))
            
            conn.commit()
            conn.close()
            await interaction.response.send_message(f"✅ Ticket #{t_id} published.", ephemeral=True)
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
        await self.tree.sync()

    async def on_ready(self):
        init_db()
        print(f'System Online: {self.user}')

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
                await channel.send(f"💼 **#{res[0]}** is now locked by {payload.member.mention}.")
            conn.close()

bot = LedgerBot()

# --- THE COMMAND LEDGER ---

@bot.tree.command(name="post_job", description="CLIENT: Create a new project ticket for workers.")
async def post_job(interaction: discord.Interaction):
    """Admin/Client tool to post work into the public channel."""
    await interaction.response.send_modal(ProjectForm())

@bot.tree.command(name="approve_work", description="CLIENT: Finalize work, log the output (clips/pages), and queue for payout.")
@app_commands.describe(ticket_id="Job ID", output_count="Number of units produced (e.g. 5 clips)")
async def approve_work(interaction: discord.Interaction, ticket_id: int, output_count: int):
    """Acts as the Auditor. Logs work into the 'Owed' ledger."""
    conn = sqlite3.connect('business_ledger.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE projects SET status = "APPROVED", units = ? WHERE ticket_id = ? AND status != "PAID"', (output_count, ticket_id))
    
    if cursor.rowcount > 0:
        await interaction.response.send_message(f"✅ Ticket #{ticket_id} moved to Pending Payouts. logged {output_count} units.")
    else:
        await interaction.response.send_message("❌ Invalid Ticket ID or status.", ephemeral=True)
    conn.commit()
    conn.close()

@bot.tree.command(name="request_revision", description="CLIENT: Send job back to worker for changes. Pauses payout.")
@app_commands.describe(ticket_id="Job ID", reason="What needs to be changed?")
async def request_revision(interaction: discord.Interaction, ticket_id: int, reason: str):
    """The Project Manager tool. DMs the worker and blocks payment until fixed."""
    conn = sqlite3.connect('business_ledger.db')
    cursor = conn.cursor()
    cursor.execute('SELECT worker_id, title FROM projects WHERE ticket_id = ?', (ticket_id,))
    row = cursor.fetchone()
    
    if row:
        cursor.execute('UPDATE projects SET status = "REVISION" WHERE ticket_id = ?', (ticket_id,))
        worker = await bot.fetch_user(row[0])
        await worker.send(f"⚠️ **Revision Required** on Job #{ticket_id} ({row[1]})\n**Note:** {reason}")
        await interaction.response.send_message(f"🔄 Revision request sent to worker.")
    else:
        await interaction.response.send_message("❌ Ticket ID not found.", ephemeral=True)
    conn.commit()
    conn.close()

@bot.tree.command(name="ledger_payouts", description="ADMIN: View total debt owed to all freelancers.")
async def ledger_payouts(interaction: discord.Interaction):
    """The Accountant's balance sheet. Shows exactly who to pay and how much."""
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("🚫 Admin Access Only.", ephemeral=True)

    conn = sqlite3.connect('business_ledger.db')
    cursor = conn.cursor()
    cursor.execute("SELECT worker_name, SUM(units) FROM projects WHERE status = 'APPROVED' GROUP BY worker_name")
    rows = cursor.fetchall()
    
    embed = discord.Embed(title="💰 Current Outstanding Debt", color=discord.Color.gold())
    if not rows:
        embed.description = "No outstanding debt. All workers are paid up."
    else:
        for name, total_units in rows:
            # Assuming 1 unit = 1 Rupee for the ledger, adjust logic if needed
            embed.add_field(name=f"Worker: {name}", value=f"Total Units: {total_units} ➔ **₹{total_units}**", inline=False)
    
    await interaction.response.send_message(embed=embed)
    conn.close()

@bot.tree.command(name="settle_all", description="ADMIN: Reset the ledger to zero after paying workers.")
async def settle_all(interaction: discord.Interaction):
    """Finalizes the payment cycle. Moves all 'Approved' jobs to 'Paid'."""
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("🚫 Admin Access Only.", ephemeral=True)

    conn = sqlite3.connect('business_ledger.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET status = 'PAID' WHERE status = 'APPROVED'")
    conn.commit()
    conn.close()
    await interaction.response.send_message("📉 Ledger Cleared. All balances reset to ₹0.")

@bot.tree.command(name="performance_report", description="ADMIN: See a summary of completed jobs per worker.")
async def performance_report(interaction: discord.Interaction):
    """The Manager's productivity report."""
    if interaction.user.id != ADMIN_ID:
        return await interaction.response.send_message("🚫 Admin Access Only.", ephemeral=True)

    conn = sqlite3.connect('business_ledger.db')
    cursor = conn.cursor()
    cursor.execute("SELECT worker_name, COUNT(ticket_id) FROM projects WHERE status = 'PAID' GROUP BY worker_name")
    rows = cursor.fetchall()
    
    embed = discord.Embed(title="📊 Productivity Report", color=discord.Color.green())
    for name, count in rows:
        embed.add_field(name=name, value=f"Finished Projects: {count}", inline=True)
    
    await interaction.response.send_message(embed=embed)
    conn.close()

if __name__ == "__main__":
    bot.run(TOKEN)
