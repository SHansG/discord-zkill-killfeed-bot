import os
from dotenv import load_dotenv

class Settings:
    def __init__(self, settings: dict) -> None:
        # self.invite_link = ""  # later put the link there
        self.bot_prefix = settings.get("prefix", "")
        self.activity = settings.get("activity", "")
        self.embed_color = int(settings.get("embed_color", "0x4b19bf"), 16)
        self.aliases_settings = settings.get("aliases", {})
        self.settings_dict = settings


class TOKENS:
    def __init__(self) -> None:
        load_dotenv()
        self.token = os.getenv("DISCORD_TOKEN")
        self.mongodb_url = os.getenv("MONGODB_URL")
        self.mongodb_name = os.getenv("MONGODB_NAME")
        self.bug_report_channel_id = int(os.getenv("ERROR_REPORT_CHANNEL_ID"))