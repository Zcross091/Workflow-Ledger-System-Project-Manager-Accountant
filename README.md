# 📊 LedgerBot: Discord Business Project Tracker

**LedgerBot** is a streamlined project management and payout tracking system designed for Discord. It allows managers to post jobs via modals, workers to claim them via reactions, and administrators to track outstanding debts across multiple servers. I have a Workflow Ledger System that automates job claims, tracks freelancer debt, and generates performance reports so you don't have to do manual math at the end of the month.

---

## 🚀 Features

*   **Job Intake Modals**: Clean, structured input for project titles, requirements, deadlines, and budgets.
*   **Reaction-Based Claiming**: Workers can claim jobs instantly by reacting with 👍.
*   **Approval Workflow**: Managers approve completed work and log billable units.
*   **Financial Tracking**: Generate "Payout Lists" to see exactly how much is owed to each worker.
*   **Multi-Server Isolation**: Data is partitioned by Guild ID, ensuring server-specific privacy and ledgers.
*   **Developer Diagnostics**: Built-in system health checks for the bot owner.

---

## 🛠️ Commands

### Manager Commands (Requires `Manage Messages`)
*   `/post_job`: Opens a modal to create a new project ticket.
*   `/approve_work [ticket_id] [units]`: Finalizes a project and moves it to the payout queue.

### Admin Commands (Requires `Administrator`)
*   `/payout_list`: Displays a summary of all workers and the total amounts owed to them.
*   `/settle_server`: Marks all approved work as "PAID," clearing the ledger for the current server.

### Developer Commands
*   `/system_status`: Displays global database stats (Restricted to Bot Owner).

---

## 🏗️ Technical Stack

*   **Language**: Python 3.8+
*   **Library**: `discord.py` (v2.0+)
*   **Database**: SQLite3 (Local file-based storage)
*   **Configuration**: `python-dotenv` for environment variable management

---

## 📥 Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/ledgerbot.git
    cd ledgerbot
    ```

2.  **Install Dependencies**
    ```bash
    pip install discord.py python-dotenv
    ```

3.  **Environment Variables**
    Create a `.env` file in the root directory and add your bot token:
    ```env
    DISCORD_TOKEN=your_bot_token_here
    ```

4.  **Configure Owner ID**
    Open `bot.py` and update the `OWNER_ID` variable with your unique Discord User ID to enable developer commands.

5.  **Run the Bot**
    ```bash
    python bot.py
    ```

---

## 📝 Database Schema

The bot automatically initializes a `business_ledger.db` file with the following structure:

| Column | Type | Description |
| :--- | :--- | :--- |
| `ticket_id` | INTEGER | Primary Key (Auto-increment) |
| `guild_id` | INTEGER | ID of the server where the job was posted |
| `status` | TEXT | OPEN, CLAIMED, APPROVED, or PAID |
| `base_pay` | REAL | The original budget amount |
| `units` | INTEGER | Final billable units/amount logged |

---

## 🤝 Contributing
Feel free to fork this project, open issues, or submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under the **Apache License 2.0**.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
