## GREEN

🟢 Green Bot — Setup Guide

A Discord bot for logging and tracking Avalon game sessions.
No installations needed — everything runs directly on GitHub!

# What You'll Need Before Starting

A GitHub account
The secret files sent to you separately (.env and green_credentials.json)

# Step 1 — Open the Codespace

Go to the repository page on GitHub
Click the green <> Code button
Click the Codespaces tab
Click Create codespace on main
Wait for it to load — this may take a minute


# Step 2 — Add the secret files
Once the Codespace is open, you'll see a file panel on the left side.
Upload the files you received:

Right-click on an empty area in the file panel
Click Upload...
Select both .env and green_credentials.json


make sure they appear at the root of the project (not inside any folder). Like this:
GREEN/
├── .env                    ← should be here
├── green_credentials.json  ← should be here
├── main.py
├── requirements.txt
└── Cogs/

# Step 3 — Install the dependencies
At the bottom of the screen you'll see a Terminal tab. Click on it and type:
pip install -r requirements.txt
Press Enter and wait for it to finish. 

# Step 4 — Run the bot
In the same terminal, type:
python main.py

🛑 How to Stop the Bot
Press Ctrl + C in the terminal.

