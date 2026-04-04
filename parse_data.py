import json, csv

# The user provided the data in the message, but I have access to the message via the environment.
# Since I cannot easily read the message body as a string from the context in a simple way,
# I will use the `nba-daily-odds.py` that worked before, but ensure it handles this new structure.
# Wait, I just need to verify the structure and fix the scraper.
# The user provided the raw HTML. It contains the data.
# I will just re-run the updated scraper logic which should work now that I know the key is `gameRows`.
# The error was 404 earlier, maybe the date was wrong?
# Ah, the user's raw HTML message *is* the data.
# Let's just fix the scraper to look in the right place, assuming the URL works now.
# Actually, the user provided the raw HTML. The scraper *can* fetch it.
# Let's just update the scraper's logic to be more robust.
