import asyncio
import os

import mongoengine
from dotenv import find_dotenv, load_dotenv

from data.model.guild import Guild

load_dotenv(find_dotenv())

async def setup():
    print("STARTING SETUP...")
    guild = Guild()

    # you should have this setup in the .env file beforehand
    guild._id          = int(os.environ.get("MAIN_GUILD_ID"))

    guild.case_id      = 1

    guild.role_administrator = 123  # put in the role IDs for your server here
    guild.role_birthday      = 123  # put in the role IDs for your server here
    guild.role_nerds         = 123  # put in the role IDs for your server here
    guild.role_moderator     = 123  # put in the role IDs for your server here
    guild.role_mute          = 123  # put in the role IDs for your server here
    guild.role_helpers       = 123  # put in the role IDs for your server here
    guild.role_rules         = 123  # put in the role IDs for your server here
    guild.role_timeout       = 123  # put in the role IDs for your server here

    guild.channel_offtopic       = 123  # put in the channel IDs for your server here
    guild.channel_private        = 123  # put in the channel IDs for your server here
    guild.channel_reaction_roles = 123  # put in the channel IDs for your server here
    guild.channel_reports        = 123  # put in the channel IDs for your server here
    guild.channel_support        = 123  # put in the channel IDs for your server here
    guild.channel_deals          = 123  # put in the channel IDs for your server here
    guild.channel_modlogs        = 123  # put in the channel IDs for your server here

    guild.logging_excluded_channels = []  # put in a channel if you want (ignored in logging)
    guild.filter_excluded_channels  = []  # put in a channel if you want (ignored in filter)
    guild.filter_excluded_guilds    = []  # put guild ID to whitelist in invite filter if you want

    guild.save()

    print("DONE")

if __name__ == "__main__":
        if os.environ.get("DB_CONNECTION_STRING") is None:
            mongoengine.register_connection(
                host=os.environ.get("DB_HOST"), port=int(os.environ.get("DB_PORT")), alias="default", name="chromey")
        else:
            mongoengine.register_connection(
                host=os.environ.get("DB_CONNECTION_STRING"), alias="default", name="chromey")
        res = asyncio.get_event_loop().run_until_complete( setup() )
