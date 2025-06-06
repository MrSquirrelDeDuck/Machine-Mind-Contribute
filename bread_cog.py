"""
Patch 30:
- Added a new Trade Hub upgrade unlocked at tier 5.
- Added `$bread reset_account` if you want to reset your account for some reason.
- Fuel is now shown in the item section of the space stats.
- High Roller Table has been moved from the Hidden Bakery to the regular Bread Shop. Everyone who purchased it in the past has received a refund.
- The gambit shop items will now, in their descriptions, show how much dough the item will be worth if you were to buy it.
- The :gem_white: gambit shop item has been removed.
- Standardized category naming scheme in the planet analysis.
- Fixed systems with :Bqueenanarchy: planets not being viewable on the full map.
- Fixed being able to spam `$bread hub contribute level full y` to level up a Trade Hub to tier 6, which would completely break it and both the galaxy and system map in the area.
- The code behind all the shops is now standardized, meaning all the shops should be formatted the same way. This will cause some slight differences from before in regards to line breaks, but everything else should be the same. Let me know if you find any issues.
- Other small internal changes, there should be no visual differences.

Internal changes:
- Gambit shop upgrades can now have multiple tiers, with each tier adding another `1 * bonus` dough to the item rolled, with the cost increading in the same way.
- Added a `Static_Cost_Mixin` class to `bread/store.py`, to be used in cases where the shop item uses `cost` to get the cost instead of `get_costs`. In these cases `get_cost_types` will not function properly. If the `Static_Cost_Mixin` is used in these shop item classes it will overwrite `get_cost_types` to work properly. Note that this will only work if the shop item uses `cost` and does not have the type of items change.)
- `account.Bread_Account` objects are now passed the JSON interface when being initialized.


(todo) test reply ping


TODO: Do not die to the plague

Migration plan to multi-server database:
All database functions take a server or a server id as an argument
JSON cog will have a dictionary of servers, each of which has a dictionary of users
there will also be the default dictionaries at the top level, JSON cog will need to flawlessly be able to load from one and save to the other
JSON cog will now take a server/server id as an argument when calling a filing cabinet, but will not alter the way filing cabinets are handled
we need a new name for the server level storage, one which encompasses several filing cabinets. Maybe Vault, maybe warehouse.

for server:
    update discord.py
    install numpy
    *possibly* run `python3 -m pip update`
    !bread admin set_max_prestige_level 3


Possible future stuff:

V portfolio shows your gain/loss over last tick
- alchemy profits
V each ascension lets you have 100 additional daily rolls
- stronger LC, or temporary LC
- big bread, rewards 500 normal bread loaves, may be made of 4 emojis

Done and posted:
V ooak leaderboard is ooaks only
V Leaderboard:
    V make leaderboard work for values, not emoji
    V make leaderboard use custom code for stonks (stretch goal)
V Gambling now has many more possible rewards, though the overall reward structure remains the same
V fixed minor gabling bug where waffles would appear but weren't acquirable (thank duck duck go for the meme)
V Multiroller now requires 24 rolls and has a better description
V portfolio command takes user argument
V added capys to the gamble chess set
V added $bread wiki command
V portfolio command now shows how your portfolio changed in the last tick
V multirollers now require compound rollers at higher levels

"""
from __future__ import annotations

import asyncio
from datetime import datetime
import json
import random
import typing
import os
import importlib
import math
import traceback
import re
import time
import io
import pytz

from os import getenv
from dotenv import load_dotenv



import discord
from discord.ext import commands
from discord.ext import tasks

import verification
import emoji
import bread.values as values
import bread.account as account
import bread.gamble as gamble
import bread.rolls as rolls
import bread.store as store
import bread.utility as utility
import bread.alchemy as alchemy
import bread.stonks as stonks
import bread.space as space
import bread.generation as generation
import bread.projects as projects

# roles
# average bread enjoyer
# bread enthusiast
# bread maniac
# galaxy bread

# bread specialist
# bread equalist


# bread channel level meanings
# 0 - never rollable
PERMISSION_LEVEL_NONE = 0
# 1 - can do leaderboards etc
PERMISSION_LEVEL_BASIC = 1
# 2 - can do alchemy and shop
PERMISSION_LEVEL_ACTIVITIES = 2
# 3 - can do bread rolls
PERMISSION_LEVEL_MAX = 3

earnable_channels = ["bread-rolls", "test", "machine-configure", "patch-notes"]
rollable_channels = ["bread", "spam", "smap"]
disallowed_channels = ["brick-jail", "nsfw", "memes", "just-capybaras", "server-meta", "best-moments", "events", 
                        "serious-channel"]

channel_permission_levels = {
    "bread-rolls": 3,
    "test": 3,
    "machine-configure": 3,
    "patch-notes": 3,
    "bread-activities": 2,
    "bread": 1,
    "spam": 1,
    "smap": 1,
}

default_guild = 958392331671830579
testing_guild = 949092523035480134

error_channel = 960884493663756317 # machine-configure

announcement_channel_ids = [958705808860921906] # bread on AC
test_announcement_channel_ids = [960871600415178783]  # test on the castle



white_pawn = "<:Wpawn:961815364319207516>"
white_rook = "<:Wrook:961815364482793492>"
white_bishop = "<:Wbishop:961815364428263435>"
white_knight = "<:Wknight:958746544436310057>"
white_queen = "<:Wqueen:961815364461809774>"
white_king = "<:Wking:961815364411478016>"

black_pawn = "<:Bpawn:961815364436635718>"
black_rook = "<:Brook:961815364377919518>"
black_bishop = "<:Bbishop:961815364306608228>"
black_knight = "<:Bknight:961815364424048650>"
black_queen = "<:Bqueen:961815364470202428>"
black_king = "<:Bking:961815364327600178>"

# 8 pawns of each color
all_chess_pieces_black = [black_pawn, black_pawn, black_pawn, black_pawn, black_pawn, black_pawn, black_pawn, black_pawn,
                            black_rook, black_rook,
                            black_bishop, black_bishop,
                            black_knight, black_knight,
                            black_queen,
                            black_king]

                    
all_chess_pieces_white = [white_pawn,white_pawn, white_pawn, white_pawn, white_pawn, white_pawn,white_pawn, white_pawn, 
                            white_rook,  white_rook,
                            white_bishop, white_bishop,
                            white_knight, white_knight,
                            white_queen,
                            white_king]

# all_stonks = [":pretzel:", ":cookie:", ":fortune_cookie:"]
main_stonks = [":pretzel:", ":cookie:", ":fortune_cookie:",  ":pancakes:"]
shadow_stonks = [":cake:", ":pizza:", ":pie:", ":cupcake:"]
all_stonks = main_stonks + shadow_stonks

####################################################
############   ASSIST FUNCTIONS  ###################
####################################################

def get_channel_permission_level(ctx: commands.Context):
    """Returns the permission level for the channel the context was invoked in.
    This will handle threads as well."""

    # First, check if the channel is actually a thread.
    # Threads are handled seperately from regular channel, and have their own restrictions.
    if isinstance(ctx.channel, discord.Thread):
        parent_channel = ctx.channel.parent
        parent_level = channel_permission_levels.get(parent_channel.name, PERMISSION_LEVEL_NONE)

        # If the permission level of the parent channel is not 2 or higher then doing stuff here isn't allowed.
        if parent_level < 2:
            return PERMISSION_LEVEL_NONE
        
        # Next, check if it's a private thread.
        # You can't do stuff in private threads, but regular threads are okay.
        if ctx.channel.is_private():
            return PERMISSION_LEVEL_NONE
        
        # If it passed all of the previous checks it's okay to use, but only activities, so not rolling.
        return PERMISSION_LEVEL_ACTIVITIES

    # If it's not a thread, get the permission level based off of the name.
    permission_level = channel_permission_levels.get(ctx.channel.name, PERMISSION_LEVEL_NONE)

    return permission_level

def get_id_from_guild(guild: typing.Union[discord.Guild, int, str]) -> str:
    """Takes in a guild, integer or string and returns the guild id as a string."""
    if isinstance(guild, int):
        return str(guild)
    elif isinstance(guild, discord.Guild):
        return str(guild.id)
    elif isinstance(guild, str):
        return guild
    else:
        # If nothing fires, raise a TypeError.
        raise TypeError(f"Incorrect guild type passed. Was expecting discord.Guild, int, or str, not {type(guild)}")

def get_guild_from_id(guild_id: typing.Union[discord.Guild, int, str]) -> discord.Guild:
    """Gets a discord.Guild object for the given guild id."""
    guild_id = get_id_from_guild(guild_id)
    return bot_ref.get_guild(int(guild_id))

def get_name_from_guild(guild: typing.Union[discord.Guild, int, str]) -> str:
    """Gets the a guild's name from a discord.Guild, int, or str object."""
    guild_object = get_guild_from_id(guild)

    # If the bot doesn't have access to this guild (like if it got kicked), then guild will be None.
    if guild_object is None:
        return f"<Unknown guild {guild}>"
    
    return guild_object.name

def get_id_from_user(user: typing.Union[discord.Member, int, str]) -> str:
    """Takes in a member, integer or string and returns the member id as a string."""
    if isinstance(user, int):
        return str(user)
    elif isinstance(user, discord.Member):
        return str(user.id)
    elif isinstance(user, str):
        return user
    else:
        # If nothing fires, raise a TypeError.
        raise TypeError(f"Incorrect user type passed. Was expecting discord.Member, int, or str, not {type(user)}")

def get_display_name(member: discord.Member) -> str:
    """Gets the display name of a discord.Member object."""
    return (member.global_name if (member.global_name is not None and member.name == member.display_name) else member.display_name)

def parse_int(argument: str) -> int:
    """Converts an argument to an integer, will remove commas along the way."""
    # If there's a decimal place then ignore everything after it.
    if "." in str(argument):
        arg = str(argument).replace(",", "")

        # Attempt to convert it to a float, this will ensure that it's something that is actually a number.
        # If this breaks then discord.py will catch it and just have the argument be None.
        # But, if this works then we know it's an actual number we're talking about.
        float(arg)

        # If the flaot conversion worked, then try to convert to an integer, but ignore what's after the decimal place.
        return int(arg[:arg.rfind(".")])
    
    # If there's no decimal place then just try to convert the argument normally.
    return int(str(argument).replace(",", ""))

def is_int(argument: str) -> bool:
    """Checks if an argument is an integer."""
    try:
        parse_int(argument)
        return True
    except ValueError:
        return False

def is_digit(string: str) -> bool:
    """Same as str.isdigit(), but will remove commas first."""
    return str(string).replace(",", "").isdigit()

def is_numeric(string: str) -> bool:
    """Same as str.isnumeric(), but will remove commas first."""
    return str(string).replace(",", "").isnumeric()

def is_decimal(string: str) -> bool:
    """Same as str.isdecimal(), but will remove commas first."""
    return str(string).replace(",", "").isdecimal()

def parse_fraction(argument: str) -> tuple[int, int]:
    """Attempts to parse an argument as a fraction.
    This will raise an exception if it's unable to, which should be caught via `try` and `except`."""

    # Each `([\d,]+)` matches a number (including commas.)
    # This means the pattern matches a number followed by a slash followed by another number.
    # So something like `5/8` will match it, but `w/o` is without a match.
    match = re.match("^([\d,]+)\/([\d,]+)$", str(argument))

    # If the match did not find anything.
    if match is None:
        raise commands.BadArgument
    
    argument = argument.replace(",", "") # Remove any commas that are in the numbers.
    parts = argument.split("/")

    numerator = int(parts[0])
    denominator = int(parts[1])

    return numerator, denominator

def is_fraction(argument: str) -> bool:
    """Returns a boolean for whether the given argument is a fraction."""
    match = re.match("^([\d,]+)\/([\d,]+)$", str(argument))

    return match is not None



####################################################
##############   JSON INTERFACE   ##################
####################################################


class JSON_interface:
    
    
    ####################################
    #####      SETUP
    
    bread_cog: Bread_cog = None

    file_path = "bread_data.json"

    default_data = {
        'load_count' : 0,
        
        'bread' : {
            # "949092523035480134" : { # guild id
            #     'guild_info' : {
            #         'name' : "",
            #         'rolling_channel' : "",
            #         'communications_channel' : "",
            #     },
                546829925890523167 : {
                        'username' : 'Melodie',
                        'total_dough' : 0,
                        'special_bread' : 0
                },
                961567735358291998 : {
                    'username' : 'artemis',
                    'total_dough' : 100,
                    'special_bread' : 1
                }
            # }
        }
        
    }

    all_guilds = list()
    data = dict()
    archived_bread_data = dict()
    accounts = dict()

    ####################################
    #####      FILE STUFF

    def internal_load(self: typing.Self) -> None:
        """Loads the Bread Game data from the JSON cog into the interface storage."""
        print("Bread JSON internal_load called")


        JSON_cog = bot_ref.get_cog("JSON")
        JSON_cog.load_all_data() 

        all_json_guilds = JSON_cog.get_list_of_all_guilds()

        print("Loading data for all guilds")
        for guild_id in all_json_guilds:
            print(f"Loading data for guild {guild_id}")
            data = JSON_cog.get_filing_cabinet("bread", create_if_nonexistent=False, guild=guild_id)
            if data is None:
                continue
            self.data[guild_id] = data
            if self.data[guild_id] is not None:
                self.all_guilds.append(guild_id)
                print(f"Loaded data for guild {guild_id}")
            
        self.archived_bread_data = JSON_cog.get_filing_cabinet("archived_bread_count", create_if_nonexistent=False, guild=default_guild)
        # self.data["bread"] = JSON_cog.get_filing_cabinet("bread", create_if_nonexistent=True)
        # self.data["archived_bread_count"] = JSON_cog.get_filing_cabinet("archived_bread_count", create_if_nonexistent=False)

        print("Load process complete.")

    
    def internal_save(
            self: typing.Self,
            JSON_cog = None
        ) -> None:
        """Saves the data in the interface storage to file via the JSON cog."""
        print("saving bread data")
        if JSON_cog is None:
            JSON_cog = bot_ref.get_cog("JSON")

        for guild_id in self.data.keys():
            JSON_cog.set_filing_cabinet("bread", self.data[guild_id], guild=guild_id)
            # JSON_cog.set_filing_cabinet("archived_bread_count", self.data[guild_id]["archived_bread_count"], guild=guild_id)
        # JSON_cog.set_filing_cabinet("bread", self.data)
        # JSON_cog.set_filing_cabinet("archived_bread_count", self.data["archived_bread_count"])
        JSON_cog.save_all_data()
        
        

    def create_backup(self: typing.Self) -> None:
        """Creates a backup of the interface storage.
        The JSON cog's create_backup function is preferred over this, as this will only save the bread data."""
        #first, make sure there's a backup folder (relative path)
        folder_path = "backup/"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        #then, we make the file
        file_name = datetime.now().strftime('bread_data_backup_%y-%-m-%-d---%H-%M-%S.json')
        with open(folder_path+file_name, 'w') as outfile:
            print('created ', file_name)
            #json_string = json.dumps(self.data, indent=2)
            json.dump(self.data, outfile)

        print("Backup Created.")



    ####################################
    #####      INTERFACE

    def get_account(
            self: typing.Self,
            user: typing.Union[discord.Member, int, str],
            guild: typing.Union[discord.Guild, int, str]
        ) -> account.Bread_Account:
        """Returns an account.Bread_Account object representing the given user's account in the bread data."""
        if guild is None:
            raise TypeError("Guild cannot be None")        
        
        index = get_id_from_user(user)
        guild_id = get_id_from_guild(guild)

        # if index in self.accounts:
        #     return self.accounts[index]
        account_raw = account.Bread_Account.from_dict(index, self.get_file_for_user(user, guild_id), self)
        # self.accounts[index] = account_raw
        return account_raw
        

    def set_account(
            self: typing.Self,
            user: typing.Union[discord.Member, int, str],
            user_account: account.Bread_Account,
            guild: typing.Union[discord.Guild, int, str]
        ) -> None:
        """Updates the bread data for a player based on an account.Bread_Account object."""
        if guild is None:   
            raise TypeError("Guild cannot be None")
        
        index = get_id_from_user(user)
        guild_id = get_id_from_guild(guild)

        # self.accounts[index] = user_account
        self.data[guild_id][index] = user_account.to_dict()

    def has_account(
            self: typing.Self,
            user: discord.Member
        ) -> bool:
        """Returns a boolean for whether the given member object has an account in the bread data."""
        index = str(user.id)
        guild = str(user.guild.id)
        return index in self.data[guild]

    def get_all_user_accounts(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str]
        ) -> list[account.Bread_Account]:
        """Returns a list containing all user accounts."""
        guild_id = get_id_from_guild(guild)
        
        #return [account.Bread_Account.from_dict(index, self.data["bread"][index]) for index in self.data["bread"]]
        output = []
        for index in self.data[guild_id]:
            if is_digit(index):
                # Mysterious "0" key account appeared, this should protect it from the daily reset.
                # If it is allowed in the daily reset it'll mess up existing account data to whatever is in it.
                if index == "0":
                    continue

                output.append(self.get_account(index, guild_id))
            # yield account.Bread_Account.from_dict(index, self.data["bread"][index])
        return output

    def get_list_of_all_guilds(self: typing.Self) -> list[str]:
        """Returns a list of all the guilds in the bread data."""
        return list(self.all_guilds)
    
    ####################################
    #####      BREAD SPACE

    def get_space_data(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str]
        ) -> dict:
        """Returns the `space` custom file."""
        return self.get_custom_file("space", guild=guild)
    
    def get_space_ascension(
            self: typing.Self,
            ascension_id: typing.Union[int, str],
            guild: typing.Union[discord.Guild, int, str],
            default: typing.Any = dict()
        ) -> dict:
        """Returns the space data for the given ascension."""
        space_data = self.get_space_data(guild=guild)

        return space_data.get(f"ascension_{ascension_id}", default)

    def get_space_map_data(
            self: typing.Self,
            ascension_id: typing.Union[int, str],
            guild: typing.Union[discord.Guild, int, str],
        ) -> dict:
        """Gets the map data for the given ascension in the given guild."""
        ascension_data = self.get_space_ascension(ascension_id, guild, dict())

        return ascension_data.get("map_data", {})

    def set_space_map_data(
            self: typing.Self,
            ascension_id: typing.Union[int, str],
            guild: typing.Union[discord.Guild, int, str],
            new_data: dict
        ) -> dict:
        """Sets the map data for the given ascension in the given guild."""
        ascension_data = self.get_space_ascension(ascension_id, guild, dict())

        space_data = self.get_space_data(guild=guild)

        ascension_data["map_data"] = new_data
        space_data[f"ascension_{ascension_id}"] = ascension_data

        self.set_custom_file("space", file_data=space_data, guild=guild)

    def get_ascension_seed(
            self: typing.Self,
            ascension_id: typing.Union[int, str],
            guild: typing.Union[discord.Guild, int, str]
        ) -> str:
        """Returns an ascension's seed, while creating one if it does not exist yet."""
        ascension_data = self.get_space_ascension(ascension_id, guild)

        if "seed" in ascension_data.keys():
            return ascension_data["seed"]
        
        # If this ascension doesn't yet have a seed, create one

        space_data = self.get_space_data(guild=guild)

        new_seed = space.generate_galaxy_seed()

        # The chance of this being needed is incredibly low, but just in case...
        if self.ascension_from_seed(guild, new_seed) is not None:
            while self.ascension_from_seed(guild, new_seed) is not None:
                new_seed = space.generate_galaxy_seed()
        
        ascension_data["seed"] = new_seed
        space_data[f"ascension_{ascension_id}"] = ascension_data

        self.set_custom_file("space", file_data=space_data, guild=guild)

        return new_seed
    
    def ascension_from_seed(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str],
            galaxy_seed: str
        ) -> typing.Union[int, None]:
        """Returns an integer (or None if nothing is found) for the ascension id that matches the given seed."""
        space_data = self.get_space_data(guild=guild)

        for key, value in space_data.items():
            try:
                if value.get("seed", None) == galaxy_seed:
                    return int(key.replace("ascension_", ""))
            except AttributeError:
                continue
        
        return None

    def get_day_seed(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str]
        ) -> str:
        """Returns the day seed for the given guild in Bread Space."""
        space_data = self.get_space_data(guild=guild)

        return space_data.get("day_seed", "31004150_will_rule_the_world")

    def get_tick_seed(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str]
        ) -> str:
        """Returns the tick seed for the given guild in Bread Space."""
        space_data = self.get_space_data(guild=guild)

        return space_data.get("tick_seed", "the_game_:3")
    
    def get_trade_hub_data(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str],
            ascension: int,
            galaxy_x: int,
            galaxy_y: int
        ) -> dict:
        """Fetches a trade hub's data from the database. An empty dict will be returned if the trade hub is not found."""
        space_data = self.get_space_data(guild)

        ascension_data = space_data.get(f"ascension_{ascension}", {})

        trade_hub_data = ascension_data.get("trade_hubs", {})

        return trade_hub_data.get(f"{galaxy_x} {galaxy_y}", {})
    
    def update_trade_hub_data(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str],
            ascension: int,
            galaxy_x: int,
            galaxy_y: int,
            new_data: dict
        ) -> None:
        """Sets the data for a trade hub to the given dictionary."""
        space_data = self.get_space_data(guild)

        ascension_data = space_data.get(f"ascension_{ascension}", {})

        trade_hub_data = ascension_data.get("trade_hubs", {})

        trade_hub_data[f"{galaxy_x} {galaxy_y}"] = new_data
        ascension_data["trade_hubs"] = trade_hub_data
        space_data[f"ascension_{ascension}"] = ascension_data

        self.set_custom_file("space", space_data, guild=guild)
    
    def update_trade_hub_levelling_data(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str],
            ascension: int,
            galaxy_x: int,
            galaxy_y: int,
            new_data: dict
        ) -> None:
        """Updates the progress of a trade hub's levelling to the given dictionary."""
        existing = self.get_trade_hub_data(guild, ascension, galaxy_x, galaxy_y)

        existing["level_progress"] = new_data

        self.update_trade_hub_data(
            guild = guild,
            ascension = ascension,
            galaxy_x = galaxy_x,
            galaxy_y = galaxy_y,
            new_data = existing
        )

    
    def update_project_data(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str],
            ascension: int,
            galaxy_x: int,
            galaxy_y: int,
            project_id: int, # Should be between 1 and 3.
            new_data: dict
        ) -> None:
        """Updates the data regarding a project's progress to the given dictionary."""
        space_data = self.get_space_data(guild)

        ascension_data = space_data.get(f"ascension_{ascension}", {})

        trade_hub_data = ascension_data.get("trade_hubs", {})

        tile_data = trade_hub_data.get(f"{galaxy_x} {galaxy_y}", {})

        project_progress = tile_data.get("project_progress", {})

        project_progress[f"project_{project_id}"] = new_data

        tile_data["project_progress"] = project_progress
        trade_hub_data[f"{galaxy_x} {galaxy_y}"] = tile_data
        ascension_data["trade_hubs"] = trade_hub_data
        space_data[f"ascension_{ascension}"] = ascension_data

        self.set_custom_file("space", space_data, guild=guild)
        
        
            
        


    ####################################
    #####      INTERFACE NICHE

    def get_custom_file(
            self: typing.Self,
            label: str,
            guild: typing.Union[discord.Guild, int, str]
        ) -> dict:
        """Returns the specific data for the given custom file."""
        guild_id = get_id_from_guild(guild)

        if label in self.data[guild_id]:
            return self.data[guild_id][label]
        else:
            return dict()

    def set_custom_file(
            self: typing.Self,
            label: str,
            file_data: dict,
            guild: typing.Union[discord.Guild, int, str]
        ) -> None:
        """Sets a custom file to the given dictionary."""
        guild_id = get_id_from_guild(guild)

        self.data[guild_id][label] = file_data

    def get_guild_info(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str]
        ) -> dict:
        """Returns the data for a specific guild."""
        guild_id = get_id_from_guild(guild)
        if "guild_info" not in self.data[guild_id].keys():
            self.data[guild_id]["guild_info"] = dict()

            guild_name = get_name_from_guild(guild_id)
            self.data[guild_id]["guild_info"]["name"] = guild_name


        return self.data[guild_id]["guild_info"]

    def set_guild_info(
            self: typing.Self,
            guild_info: dict,
            guild: typing.Union[discord.Guild, int, str]
        ) -> None:
        """Sets a guild's data to the given dictionary."""
        guild_id = get_id_from_guild(guild)
        self.data[guild_id]["guild_info"] = guild_info

    def get_rolling_channel(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str]
        ) -> str:
        """Gets the id of the rolling channel for the given guild."""
        guild_info = self.get_guild_info(guild)
        if "rolling_channel" not in guild_info.keys():
            return "<#967544442468843560>" # bread roll channel link in default guild
        return guild_info["rolling_channel"]
    
    def get_approved_admins(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str]
        ) -> list[str]:
        """Gives a list of user ids for the approved admins in the given guild."""
        guild_data = self.get_guild_info(guild)
        return guild_data.get("approved_admins", [])


    ####################################
    #####      INTERFACE OLD

    

    def get_file_for_user(
            self: typing.Self,
            user: typing.Union[discord.Member, int, str],
            guild: typing.Union[discord.Guild, int, str]
        ) -> dict: 
        """Gets the dictionary of the given member's stats."""
        guild_id = get_id_from_guild(guild)
        if guild_id not in self.data.keys():
            self.data[guild_id] = dict()

        key = get_id_from_user(user)
        #print("Searching database for file for "+user.display_name)
        if key in self.data[guild_id]:
            #print("Found")
            # set the guild_id if it's not already set
            if "guild_id" not in self.data[guild_id][key].keys():
                self.data[guild_id][key]["guild_id"] = guild_id

            return self.data[guild_id][key]
        else:
            print("Creating new data for "+str(user))
            guild = bot_ref.get_guild(int(guild_id))
            member = guild.get_member(int(key))
            new_file = {
                'total_dough' : 0,
                'earned_dough' : 0,
                'max_daily_rolls' : 10,
                'username' : member.name,
                'display_name' : get_display_name(member),
                'id' : member.id,
                'guild_id' : guild_id,
            }
            self.data[guild_id][key] = new_file
            return new_file
        





########################################################################################################################################
###############   BREAD COG   ######################
####################################################


class Bread_cog(commands.Cog, name="Bread"):

    json_interface = JSON_interface()
    currently_interacting = list()

    def __init__(
            self: typing.Self,
            bot: commands.Bot
        ) -> None:
        self.bot = bot
        self.daily_task.start()

        bot.json_interface = self.json_interface
        self.json_interface.bread_cog = self

    def cog_unload(self: typing.Self):
        self.daily_task.cancel()
        pass

    def scramble_random_seed(self: typing.Self) -> None:
        """Scrambles the random seed to make it harder to predict."""
        try:
            system_random = random.SystemRandom()
            
            all_guilds = self.json_interface.all_guilds

            # Get the stonk data to use the shadow stonk values of a randomly selected guild.
            stonks_file = self.json_interface.get_custom_file("stonks", guild = system_random.choice(all_guilds))

            stonk_values = []
            for stonk in shadow_stonks:
                stonk_values.append(stonks_file.get(stonk, system_random.randint(25, 1000)))
            
            system_random.shuffle(stonk_values)

            base = int.from_bytes(os.urandom(16))
            mod = int.from_bytes(os.urandom(1024))
            sum_mult_1 = stonk_values[0] * stonk_values[1]
            sum_mult_2 = stonk_values[2] * stonk_values[3]

            seed = int(base * (sum_mult_1 / sum_mult_2)) * mod

            random.seed(seed)
        except:
            random.seed(os.urandom(1024))
    
    def remove_from_interacting(
            self: typing.Self,
            user_id: int
        ) -> None:
        """Attempts to remove the given user id from the interacting list, but catches the exception raised if it is not in the list to begin with."""
        try:
            self.currently_interacting.remove(user_id)
        except ValueError:
            pass
    
    def describe_added_shop_items(
            self: typing.Self,
            before: list | set,
            after: list | set
        ) -> str:
        """Gives a description of added shop items based on a list of available shop items prior to something happening and a list for after it happened."""
        # Becuase of how the Ephemeral Upgrades work their can_be_purchased will toggle when any are purchased,
        # resulting in the text "*The .*" being added to the buy message. While is this absolutely hilarious it
        # is unfortunately not intended, will likely cause confusion, and should not be in the game. These two
        # filters will clear out any ephemeral upgrades that are in the before or after lists.
        before = filter(lambda i: not issubclass(i, store.Ephemeral_Upgrade), before)
        after = filter(lambda i: not issubclass(i, store.Ephemeral_Upgrade), after)
        
        difference = list(set(after) - set(before)) # What's in the end but not the start.
        
        added = ""
        
        if difference: # If it has any contents.
            added = "\n\n*The "
            
            shop_data = {
                "Bread Shop": [],
                "Hidden Bakery": [],
                "Gambit Shop": [],
                "Space Shop": [],
                "Salvage Shop": []
            }
            
            for item in difference:
                if item in store.normal_store_items:
                    shop_data["Bread Shop"].append(item)
                elif item in store.prestige_store_items:
                    shop_data["Hidden Bakery"].append(item)
                elif item in store.gambit_shop_items:
                    shop_data["Gambit Shop"].append(item)
                elif item in store.space_shop_items:
                    shop_data["Space Shop"].append(item)
                elif item in store.all_salvage_shop_items:
                    shop_data["Salvage Shop"].append(item)

            filtered = {name: contents for name, contents in shop_data.items() if contents}

            # The goal is to have something that looks like this:
            # The __, __, and __ shop items have been added to the Bread Shop, the __ and __ items to the Hidden Bakery, and the __ shop item to the Space Shop.
            
            for shop_index, data in enumerate(filtered.items()):
                shop_name, items = data
                
                if shop_index != 0:
                    if shop_index == len(filtered) - 1:
                        added += ", and the "
                    else:
                        added += ", the "
                
                added += utility.list_items([item.display_name for item in items])
                
                if shop_index == 0:
                    added += " shop"
                
                added += " item"
                
                if len(items) > 1:
                    added += "s"
                
                if shop_index == 0:
                    if len(items) == 1:
                        added += " has"
                    else:
                        added += " have"
                    
                    added += f" been added to the {shop_name}"
                else:
                    added += f" to the {shop_name}"
            
            added += ".*"
        
        return added
    

    ########################################################################################################################
    #####      TASKS

    reset_time = None

    @tasks.loop(minutes=60)
    async def daily_task(self: typing.Self):
        # NOTE: THIS LOOP CANNOT BE ALTERED ONCE STARTED, EVEN BY RELOADING. MUST BE STOPPED MANUALLY
        time = datetime.now()
        print (time.strftime("Hourly bread loop running at %H:%M:%S"))
        
        # Scramble the random seed.
        # The seed doesn't really need to be scrambled every hour, but it doesn't hurt.
        self.scramble_random_seed()

        self.synchronize_usernames_internal()
        self.json_interface.internal_save() # Save every hour
        self.currently_interacting.clear() # Clear the list of users currently interacting
        
        hour = time.hour # This is in UTC.
        
        def in_dst():
            timezone = pytz.timezone("US/Pacific")
            timezone_aware_date = timezone.localize(time, is_dst=None)
            return timezone_aware_date.tzinfo._dst.seconds != 0
        
        # If it's not DST in PST add 1 to the hour.
        # Datetime math is the bane of my existence, but this does seem to work.
        if not in_dst():
            print(f"Hourly loop is not currently in DST. Changing {hour} to {hour - 1}")
            hour -= 1
            
        # Account for the time zone difference between PST and UTC.
        hour -= 7
        
        print(f"Current hour in PDT should be {hour}.")

        #run at 3pm
        if hour == 15:
            # self.json_interface.create_backup()
            self.reset_internal() # this resets all roll counts to 0
            print("Daily reset called")
            await self.announce("bread_o_clock", "It's Bread O'Clock!")

        # every 6 hours, based around 3pm
        # print (f"Hour +15 %6 is {(hour + 15) % 6}")
        # print (f"Hour -15 %6 is {(hour - 15) % 6}")
        if (hour - 12) % 6 == 0:
            self.space_tick()

            print("stonk fluctuate called")

            self.stonk_fluctuate_internal()
            await self.stonks_announce()
    
    def space_tick(self: typing.Self) -> None:
        """Bread Space related tasks that run at stonk ticks."""

        all_guild_ids = self.json_interface.get_list_of_all_guilds()
        for guild_id in all_guild_ids:
            space_data = self.json_interface.get_space_data(guild=guild_id)

            # Set a new tick seed.
            space_data["tick_seed"] = space.generate_galaxy_seed()

            self.json_interface.set_custom_file("space", file_data=space_data, guild=guild_id)
    
    @daily_task.before_loop
    async def before_daily(self: typing.Self):
        # This just waits until it's time for the first iteration.
        print("Starting Bread cog hourly loop, current time is {}.".format(datetime.now()))

        minute_in_hour = 5 # 5 would be X:05, 30 would be X:30.

        wait_time = time.time() - (minute_in_hour * 60)
        wait_time = 3600 - (wait_time % 3600) + 2 # Artificially add 2 seconds to ensure it stops at the correct time.

        print("Waiting to start Bread cog hourly loop for {} minutes.".format(round(wait_time / 60, 2)))
        
        await asyncio.sleep(wait_time)
        
        print("Finished Bread cog hourly loop waiting at {}.".format(datetime.now()))
    
    @commands.Cog.listener()
    async def on_command_error(
            self: typing.Self,
            ctx: commands.Context,
            error: typing.Type[Exception]
        ):
        # If a check failed like the is_owner check or the approved admin check.
        if isinstance(error, commands.errors.CheckFailure):
            return
        
        # If someone tried to run a command that doesn't exist.
        if isinstance(error, commands.errors.CommandNotFound):
            return
        
        # If something went wrong with discord.py's argument parsing.
        # Something like `$brick the "j` will trigger this due to the lack of a closing double quotation mark.
        if isinstance(error, commands.errors.ArgumentParsingError):
            return
        
        output = "\n".join(traceback.format_exception(error))

        # Print the error to the terminal so it can be seen.
        print(output)

        try:
            # Attempt to fetch the error log channel, if the bot doesn't have access then discord.errors.Forbidden will be raised.
            channel = await self.bot.fetch_channel(error_channel)
        except discord.errors.Forbidden:
            # If this happened that means it doesn't have access to the error channel, so don't make another error by trying to send the log anyway.
            return

        # Format the error in an embed to supress pings and make it a little nicer to see while panicking.
        embed = discord.Embed(
            title = "Machine-Mind error",
            description = f"[Trigger message.](<{ctx.message.jump_url}>)\n```{output}```",
            color=8884479,
        )
        
        # Send the actual message with the generated embed.
        await channel.send(embed=embed)

    
    ########################################################################################################################
    #####      ANNOUNCE

    previous_messages = dict()

    async def announce(
            self: typing.Self,
            key: str,
            content: str
        ) -> None:
        """Announces the given content to all guilds.
        
        The key argument is used to generate the save key, which is used to store previous messages and delete them when the next one is sent."""

        print("announce called")
        # load_dotenv()
        # IS_PRODUCTION = getenv('IS_PRODUCTION')
        # if IS_PRODUCTION == 'False':
        #     return
        print("announce continuing")

        for guild_id in self.json_interface.get_list_of_all_guilds():
            guild_info = self.json_interface.get_guild_info(guild_id)
            if "announcement_channel" not in guild_info.keys():
                continue
            channel_id = guild_info["announcement_channel"]
            channel = self.bot.get_channel(int(channel_id))
            if channel is None:
                print(f"Channel not found for guild {guild_id}")
                continue
            # save message and delete previous one
            # first create a key we'll use to refer to each one
            save_key = str(key) + str(guild_id)
            try:
                await self.previous_messages[save_key].delete()
                self.previous_messages.pop(save_key)
            except:
                print(f"message deletion failed for {save_key}")
                pass
            try:
                message = await channel.send(content)
                self.previous_messages[save_key] = message
            except:
                print(f"message sending failed for {save_key}")
                pass


        # for channel_id in announcement_channel_ids:
        #     channel = self.bot.get_channel(int(channel_id))
        #     if channel is not None:
        #         # save message and delete previous one
        #         # first create a key we'll use to refer to each one
        #         save_key = str(key) + str(channel_id)

        #         if save_key in self.previous_messages:
        #             try:
        #                 await self.previous_messages[save_key].delete()
        #                 self.previous_messages.pop(save_key)
        #             except:
        #                 pass
        #             try:
        #                 message = await channel.send(message)
        #                 self.previous_messages[save_key] = message
        #             except:
        #                 pass

    ########################################################################################################################
    #####      SYNCHRONIZE_USERNAMES

    def synchronize_usernames_internal(self: typing.Self) -> None:
        """Syncronizes the internally stored usernames with the actual usernames of members."""
        # we get the guild and then all the members in it
        # guild = default_guild

        for guild_id in self.json_interface.get_list_of_all_guilds():
            # guild = self.bot.get_guild(default_guild)
            guild = self.bot.get_guild(int(guild_id))

            # If the bot doesn't have access to the guild. For example, if the bot was kicked.
            if guild is None:
                continue

            all_members = guild.members
            
            print(f"synchronizing usernames for guild {get_name_from_guild(guild)}")
            print(f"member count is {len(all_members)}, theoretical amount is {guild.member_count}")

            if len(all_members) != guild.member_count:
                print("member count mismatch")

            # we iterate through all the members and rename the key
            for member in all_members:
                # make sure they have an account
                # print (f"Checking {member.display_name}")
                if self.json_interface.has_account(member):
                    #print(f"{member.display_name} has account")
                    # get the account
                    account = self.json_interface.get_account(member, guild=guild_id)

                    account.values["id"] = member.id
                    account.values["username"] = member.name
                    #account.values["display_name"] = member.display_name
                    account.values["display_name"] = get_display_name(member)
                    
                    # save the account
                    self.json_interface.set_account(member, account, guild=guild_id)

        # save the database      
        self.json_interface.internal_save()
        
        

    ########################################################################################################################
    #####      BREAD

    @commands.group(
        brief="Bread.",
        help="It's bread.\n\nUse '$bread wiki' to get a link to the knowledge repository."
    )
    async def bread(self, ctx): #, *args):
        #print("bread called with "+str(len(args))+" args: "+str(args))

        #print(f"bread invoked with passed subcommand {ctx.subcommand_passed}")

        if ctx.invoked_subcommand is None:
            user_account = self.json_interface.get_account(ctx.author, guild=ctx.guild.id)
            spellcheck = user_account.get("spellcheck")
            if spellcheck is False or ctx.subcommand_passed == None:
                await self.roll(ctx)
            else:
                await ctx.send("That is not a recognized command. Use `$help bread` for some things you could call. If you wish to roll, use `$bread` on its own.")

        pass
    
    @bread.command(
        hidden = True,
        brief = "Shows this message."
    )
    async def help(self, ctx, *, subcommand: typing.Optional[str] = commands.parameter(description = "A subcommand to get the help for.")):
        if subcommand is None:
            subcommand = ""

        command = bot_ref.get_command(f"bread {subcommand}")

        if command is None:
            await ctx.reply("I can't find that command.")
            return

        await ctx.send_help(command)

    ########################################################################################################################
    #####      BREAD WIKI

    @bread.command(
        brief="Links to the wiki."
    )
    async def wiki(self, ctx):
        await ctx.send("The bread wiki is a repository of all information so far collected about the bread game. It can be found here:\nhttps://bread.miraheze.org/wiki/The_Bread_Game_Wiki")

    ###########################################################################################################################
    ######## STATS OLD

    @bread.command(
        hidden = True,
        brief="Stats about bread.",
        help="Gives bread stats about either the person calling it or the named user."
    )
    async def stats_old(self, ctx,
            user: typing.Optional[discord.Member] = commands.parameter(description = "The user to get the stats of."),
            archived: typing.Optional[str] = commands.parameter(description = "Use 'archived' to use the archived data.")
            ):
        items = {}
        for item in values.all_emotes:
            items[item.text] = len(item.text)
        print(items)
        print(list(sorted(items, key=items.get)))
        #print("stats called for user "+str(user))

        check_archive = False
        if (archived is not None) and (archived.lower() == "archive" or archived.lower() == "archived"):
            check_archive = True

        if user is None:
            user = ctx.author


        output = ""

        #archive check
        if check_archive is False:
            #getting current data
            file = self.json_interface.get_file_for_user(user, ctx.guild.id)
            file["username"] = user.name
        else:
            #getting archived data
            old_data = self.json_interface.archived_bread_data

            if old_data is None:
                await ctx.send(f"No archive data found for {user.name}")
                return
            
            id_str = str(user.id)
            #print(f"Searching for {id_str} in archived data {old_data.keys()}")
            if id_str in old_data.keys():
                file = old_data[id_str]
            else:
                await ctx.send(f"No archive data found for {user.name}")
                return

        output += "Stats for: " + file["username"] + "\n\n"
        output += "You have **" + str(file["total_dough"]) + " dough.**\n\n"
        if "earned_dough"in file.keys():
            output += "You've found " + str(file["earned_dough"]) + " dough through all your rolls.\n"
        if "total_rolls" in file.keys():
            output += "You've bread rolled " + Bread_cog.write_number_of_times( str(file["total_rolls"]) ) + ".\n"
            pass

        if "lifetime_gambles" in file.keys():
            output += "You've gambled your dough " + Bread_cog.write_number_of_times( str(file["lifetime_gambles"]) ) + ".\n"
            pass

        if "max_daily_rolls" in file.keys():
            output += "\nYou can bread roll " + Bread_cog.write_number_of_times( str(file["max_daily_rolls"]) ) + " each day.\n"
            pass
        if ("loaf_converter" in file.keys()) and (file["loaf_converter"] > 0):
            output += f"You have {utility.write_count( file['loaf_converter'], 'Loaf Converter'  )}.\n"
            pass
        if ("multiroller" in file.keys()) and (file["multiroller"] > 0):
            output += f"With your {utility.write_count( file['multiroller'], 'Multiroller'  )}, you roll {utility.write_number_of_times(2 ** file['multiroller'])} with each command.\n"
        output += "\nIndividual stats:\n"
        if ":bread:" in file.keys():
            output += ":bread: - " + str(file[":bread:"]) + " found.\n"

        

        #list all emojis found
        for key in file.keys():   
            if key.startswith(":") and key.endswith(":") and key != ":bread:" and (file[key] != 0):
                output += key + " - " + str(file[key]) + "\n"
            pass

        #list all special emojis
        for key in file.keys():   
            if key.startswith("<") and key.endswith(">") and key not in all_chess_pieces_black and key not in all_chess_pieces_white:
                output += key + " - " + Bread_cog.write_number_of_times( str(file[key]) ) + ".\n"
            pass
        
        #make chess board
        board = self.format_chess_pieces(file)
        if board != "":
            output += "\n" + board + "\n"
        
        if "lottery_win"in file.keys() and file["lottery_win"] != 0:
            output += "You've won the lottery " + Bread_cog.write_number_of_times( str(file["lottery_win"]) ) + "!\n\n"
        if "chess_pieces"in file.keys() and file["chess_pieces"] != 0:
            output += "You've found a chess piece " + Bread_cog.write_number_of_times( str(file["chess_pieces"]) ) + ".\n"
        if "special_bread" in file.keys() and file["special_bread"] != 0:
            output += "You've found special bread " + Bread_cog.write_number_of_times( str(file["special_bread"]) ) + ".\n"
        if "highest_roll" in file.keys() and file["highest_roll"] > 10:
            output += "The highest roll you've found so far is " + str(file["highest_roll"]) + ".\n"
        if "twelve_breads" in file.keys():
            output += "You've found twelve bread " + Bread_cog.write_number_of_times( str(file["twelve_breads"]) )+ ".\n"
        if "eleven_breads" in file.keys():
            output += "You've found eleven bread " + Bread_cog.write_number_of_times( str(file["eleven_breads"]) ) + ".\n"
        if "ten_breads" in file.keys():
            output += "You've found the full ten loaves " + Bread_cog.write_number_of_times( str(file["ten_breads"]) ) + ".\n"
        if "natural_1" in file.keys():
            output += "You rolled a single solitary bread " + Bread_cog.write_number_of_times( str(file["natural_1"]) ) + ".\n"

        await ctx.send(output)

    ###########################################################################################################################
    ######## BREAD STATS NEW

    @bread.command(
        brief="Stats about bread.",
        help="Gives bread stats about either the person calling it or the named user. Call as '$bread stats [user]' to get stats about another person. Call as '$bread stats [user] archive' to get stats about the user's archive, or as '$bread stats [user] chess' to get stats about the user's chess piece collection."
    )
    async def stats(self, ctx,
            user: typing.Optional[discord.Member] = commands.parameter(description = "The user to get the stats of."),
            modifier: typing.Optional[str] = commands.parameter(description = "The modifier for the stats. Like 'chess', 'gambit', or 'space'.")
            ):
        #print("stats called for user "+str(user))

        # make sure we're in the right channel to preven spam
        #if ctx.channel.name not in rollable_channels and ctx.channel.name not in earnable_channels:
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_BASIC:
            await ctx.send("Sorry, you can't do that here.")
            return
        
        archive_keywords = ["archive", "archived"]
        chess_keywords = ["chess", "chess pieces", "pieces"]
        gambit_keywords = ["gambit", "strategy", "gambit shop", "strategy shop"]
        space_keywords = ["space"]
        item_keywords = ["item", "items", "inventory"]
        all_keywords = archive_keywords + chess_keywords + gambit_keywords + space_keywords + item_keywords

        if user is not None and modifier is None:
            names = [user.name, user.nick, user.global_name, user.display_name]
            matches = [name.lower() in all_keywords for name in names if isinstance(name, str)]
            if any(matches):
                user = None
                modifier = names[matches.index(True)]
            

        if modifier is not None and modifier.lower() in archive_keywords:
            # just call the old version, not worth it to try and implement it since accounts don't really understand
            # the existence of the archive
            await self.stats_old(ctx, user, modifier)
            return

        
        # new stats command
        
        output = ""

        if user is None:
            user = ctx.author
        print(f"stats called for user {user.display_name} by {ctx.author.display_name}")

        # get account
        user_account = self.json_interface.get_account(user, ctx.guild.id) # type: account.Bread_Account

        # bread stats space
        if (modifier is not None) and modifier.lower() in space_keywords:
            await self.space_stats(ctx, user)
            return

        # bread stats items
        if (modifier is not None) and modifier.lower() in item_keywords:
            output = f"Item stats of {user_account.get_display_name()}:\n\n"
            
            if user_account.has(":bread:"):
                output += f":bread: - {utility.smart_number(user_account.get(':bread:'))}\n"

            display_list = ["special_bread", "rare_bread", "misc_bread", "shiny", "shadow", "misc", "unique" ]

            #iterate through all the display list and print them
            for item_name in display_list:

                display_items = user_account.get_all_items_with_attribute(item_name)

                for item in display_items:
                    if not user_account.has(item.text):
                        continue
                    
                    output += f"{utility.smart_number(user_account.get(item.text))} {item.text} , "
                
                # Remove the last `, ` if it exists.
                output = output.removesuffix(", ")
                
                # If there isn't a `\n` at the end, add one.
                # There will be a `\n` at the end if we didn't add anything in this iteration.
                if not output.endswith("\n"):
                    output += "\n"
            
            await ctx.reply(output)
            return

        # bread stats chess
        if modifier is not None and modifier.lower() in chess_keywords:
            output = f"Chess pieces of {user_account.get_display_name()}:\n\n"
            for chess_piece in values.all_chess_pieces:
                output += f"{chess_piece.text} - {user_account.get(chess_piece.text)}\n"
            
            if any(user_account.has(piece.text) for piece in values.all_anarchy_pieces):
                output += "\n"
                for anarchy_piece in values.all_anarchy_pieces:
                    output += f"{anarchy_piece.text} - {user_account.get(anarchy_piece.text)}\n"


            await ctx.send(output)
            return

        # bread stats gambit
        if modifier is not None and modifier.lower() in gambit_keywords:
            output = f"Gambit shop bonuses for {user_account.get_display_name()}:\n\n"
            boosts = user_account.values.get("dough_boosts", {})
            for item in boosts.keys():
                output += f"{item} - {boosts[item]}\n"
            if len(boosts) == 0:
                output += "You have not bought any gambit shop upgrades yet."
            await ctx.send(output)
            return

        sn = utility.smart_number

        output += f"Stats for: {user_account.get_display_name()}:\n\n"
        output += f"You have **{sn(user_account.get_dough())} dough.**\n\n"
        if user_account.has("earned_dough"):
            output += f"You've found {sn(user_account.get('earned_dough'))} dough through all your rolls and {sn(self.get_portfolio_combined_value(user.id, guild=ctx.guild.id))} dough through stonks.\n"
        if user_account.has("total_rolls"): 
            output += f"You've bread rolled {user_account.write_number_of_times('total_rolls')} overall.\n"
        
        if user_account.has("lifetime_gambles"):
            output += f"You've gambled your dough {user_account.write_number_of_times('lifetime_gambles')}.\n"
        if user_account.has("max_daily_rolls"):
            if user_account.get('daily_rolls') < 0:
                output += f"You have {sn(-user_account.get('daily_rolls'))} stored rolls, plus a maximum of {sn(user_account.get('max_daily_rolls'))} daily rolls.\n"
            else:
                output += f"You've rolled {sn(user_account.get('daily_rolls'))} of {user_account.write_number_of_times('max_daily_rolls')} today.\n"
        if user_account.get('max_days_of_stored_rolls') > 1:
            output += f"You can store rolls for up to {user_account.get('max_days_of_stored_rolls')} days.\n"
        if user_account.has("loaf_converter"):
            output += f"You have {user_account.write_count('loaf_converter', 'Loaf Converter')}"  
            if user_account.has("LC_booster"):
                LC_booster_level = user_account.get("LC_booster")
                multiplier = 1
                if LC_booster_level >= 1:
                    multiplier = 2 ** LC_booster_level 
                boosted_amount = user_account.get("loaf_converter") * multiplier
                output += f", which, with Recipe Refinement level {LC_booster_level}, makes you {utility.smart_number(boosted_amount)} times more likely to find special items.\n"
            else:
                output += ".\n"
        if user_account.has(values.omega_chessatron.text):
            output += f"With your {user_account.write_count(values.omega_chessatron.text, 'Omega Chessatron')}, each new chessatron is worth {sn(user_account.get_chessatron_dough_amount(True))} dough.\n"
        if user_account.has("multiroller"):
            output += f"With your {user_account.write_count('multiroller', 'Multiroller')}, you roll {utility.write_number_of_times(2 ** user_account.get('multiroller'))} with each command. "
            if user_account.has("compound_roller"):
                output += f"You also get {utility.write_count(2 ** user_account.get('compound_roller'), 'roll')} per message with your {user_account.write_count('compound_roller', 'Compound Roller')}.\n"
            else:
                output += "\n"
        if user_account.has("gamble_level"):
            output += f"You have level {user_account.get('gamble_level')} of the High Roller Table.\n"

        # ascension/prestige shop items
        if user_account.has("prestige_level", 1):
            output += "\n"
            if user_account.has("max_daily_rolls_discount"):
                output += f"You have {utility.write_count(user_account.get('max_daily_rolls_discount'), 'Daily Discount Card')}.\n"
            if user_account.has("loaf_converter_discount"):
                output += f"You have {utility.write_count(user_account.get('loaf_converter_discount'), 'Self Converting Yeast level')}.\n"
            if user_account.has ("chess_piece_equalizer"):
                output += f"With level {user_account.get('chess_piece_equalizer')} of the Chess Piece Equalizer, you get {store.chess_piece_distribution_levels[user_account.get('chess_piece_equalizer')]}% white pieces.\n"
            if user_account.has("moak_booster"):
                output += f"With level {user_account.get('moak_booster')} of the Moak Booster, you get {round((store.moak_booster_multipliers[user_account.get('moak_booster')]-1)*100)}% more Moaks.\n"
            if user_account.has("chessatron_shadow_boost"):
                output += f"With level {user_account.get('chessatron_shadow_boost')} of the Chessatron Contraption, your Omega Chessatrons are {round(user_account.get_shadowmega_boost_amount() * 100 - 100)}% more powerful than normal.\n"
            if user_account.has("shadow_gold_gem_luck_boost"):
                output += f"With level {user_account.get('shadow_gold_gem_luck_boost')} of Ethereal Shine, you get {utility.write_count(user_account.get_shadow_gold_gem_boost_count(), 'more LC')} worth of gem luck.\n"
            if user_account.has("first_catch_level"):
                output += f"With First Catch of the Day, your first {utility.write_count(user_account.get('first_catch_level'), 'special item')} each day will be worth 4x more.\n"
            if user_account.has("fuel_refinement"):
                output += f"You get {round(user_account.get_fuel_refinement_boost() * 100 - 100)}% more fuel with {user_account.write_count('fuel_refinement', 'level')} of Fuel Refinement.\n"
            if user_account.has("corruption_negation"):
                output += f"You have a {round(abs(user_account.get_corruption_negation_multiplier() * 100 - 100))}% lower chance of a loaf becoming corrupted with {user_account.write_count('corruption_negation', 'level')} of Corruption Negation.\n"

        output_2 = ""

        output_2 += "\nIndividual stats:\n"
        if user_account.has(":bread:"):
            output_2 += f":bread: - {sn(user_account.get(':bread:'))}\n"

        # list all special breads
        # special_breads = user_account.get_all_items_with_attribute("special_bread")
        # selected_special_breads = list()
        # for i in range(len(special_breads)):
        #     # skip the ones that are also rare
        #     if "rare_bread" in special_breads[i].attributes:
        #         continue
            
        #     if user_account.has(special_breads[i].text):
        #         selected_special_breads.append(special_breads[i])

        # for i in range(len(selected_special_breads)):

        #     text = selected_special_breads[i].text

        #     output_2 += f"{user_account.get(text)} {text} "
        #     if i != len(selected_special_breads) - 1:
        #         output_2 += ", "
        #     else:
        #         output_2 += "\n"

        display_list = ["special_bread", "rare_bread", "misc_bread", "shiny", "shadow", "misc", "unique" ]

        #iterate through all the display list and print them
        for item_name in display_list:

            display_items = user_account.get_all_items_with_attribute(item_name)

            cleaned_items = []
            for display_item in display_items:

                if user_account.has(display_item.text, 1):
                    cleaned_items.append(display_item)
                    # remove the item from the list if it's quantity zero           

            for i in range(len(cleaned_items)):

                text = cleaned_items[i].text
                # if user_account.get(text) == 0:
                #     continue #skip empty values
                output_2 += f"{sn(user_account.get(text))} {text} "
                if i != len(cleaned_items) - 1:
                    output_2 += ", "
                else:
                    output_2 += "\n"

        output_3 = ""

        #make chess board
        board = self.format_chess_pieces(user_account.values)
        if board != "":
            output_3 += "\n" + board + "\n"

        # list highest roll stats

        if user_account.has("highest_roll", 11):
            output_3 += f"Your highest roll was {user_account.get('highest_roll')}.\n"
            comma = False
            if user_account.has("eleven_breads"):
                output_3 += f"11 - {user_account.write_number_of_times('eleven_breads')}"
                comma = True
            if user_account.has("twelve_breads"):
                if comma:
                    output_3 += ", "
                output_3 += f"12 - {user_account.write_number_of_times('twelve_breads')}"
                comma = True
            if user_account.has("thirteen_breads"):
                if comma:
                    output_3 += ", "
                output_3 += f"13 - {user_account.write_number_of_times('thirteen_breads')}"
                comma = True
            if user_account.has("fourteen_or_higher"):
                if comma:
                    output_3 += ", "
                output_3 += f"14+ - {user_account.write_number_of_times('fourteen_or_higher')}"
                comma = True
            if comma:
                output_3 += "."
            output_3 += "\n"

        # list 10 and 1 roll stats
        output_3 += f"You've found a single solitary loaf {user_account.write_number_of_times('natural_1')}, and the full ten loaves {user_account.write_number_of_times('ten_breads')}.\n"

        # list the rest of the stats

        if user_account.has("lottery_win"):
            output_3 += f"You've won the lottery {user_account.write_number_of_times('lottery_win')}!\n"
        if user_account.has("chess_pieces"):
            output_3 += f"You have {user_account.write_count('chess_pieces', 'Chess Piece')}.\n"
        if user_account.has("special_bread"):
            output_3 += f"You have {user_account.write_count('special_bread', 'Special Bread')}.\n"
        
        if len(output) + len(output_2) + len(output_3) < 1900:
            await ctx.reply(output + output_2 + output_3)
        elif len(output) + len(output_2) < 1900:
            await ctx.reply(output + output_2)
            await ctx.reply("Stats continued:\n" + output_3)
        else:
            await ctx.reply(output)
            await ctx.reply("Stats continued:\n" + output_2)
            await ctx.reply("Stats continued:\n" + output_3)
        # await ctx.reply(output)

        #await self.do_chessboard_completion(ctx)

            
            

    
    ###########################################################################################################################
    ######## BREAD EXPORT

    @bread.command(
        brief="Exports your stats data",
        help = "Exports your or somebody else's stats into a JSON file.",
        aliases = ["dump"]
    )
    async def export(self, ctx,
            person: typing.Optional[discord.Member] = commands.parameter(description = "Who to export the stats of."),
        ):
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_BASIC:
            await ctx.reply(f"You can't do that here, please do it in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        if person is None:
            person = ctx.author

        user_account = self.json_interface.get_account(person, ctx.guild)

        file_text = json.dumps(user_account.values, indent=4)

        fake_file = io.StringIO(file_text)
        final_file = discord.File(fake_file, filename="export.json")

        await ctx.reply(file=final_file)

            
            

    
    ###########################################################################################################################
    ######## BREAD LEADERBOARD

    @bread.command(
        brief="Shows the top earners.",
        help = 
"""Used to see the rankings for any stat or emoji that is tracked. 

Include the word "all" to see the leaderboard for all players, including those of a different ascension level. Include "wide" for a wider leaderboard.

Some of the ones you can use include:

total_dough
earned_dough
portfolio_value
max_daily_rolls
total_rolls

natural_1
ten_breads
eleven_breads
twelve_breads
thirteen_breads
fourteen_or_more
lottery_win

special_bread
rare_bread
chess_pieces

multiroller
loaf_converter""",
        aliases = ["leaderboards", "lb"]
    )
    async def leaderboard(self, ctx,
            person: typing.Optional[discord.User] = commands.parameter(description = "The person to highlight in the leaderboard."),
            *args # Can't use argument parameters here.
            ):

        print(f"Leaderboard called by {ctx.author} for {args}")

        args = list(args)

        if person is None:
            person = ctx.author
        
        search_value = None
        lifetime = False
        search_all = False
        wide_leaderboard = False
        ascensions = []
        requester_account = self.json_interface.get_account(ctx.author.id, ctx.guild.id)

        if "lifetime" in args:
            lifetime = True
            args.remove("lifetime")

        if "all" in args:
            search_all = True
            args.remove("all")

        if "wide" in args:
            wide_leaderboard = True
            args.remove("wide")
        
        for arg in args.copy():
            if arg.startswith("a") and is_numeric(arg[1:]):
                ascensions.append(parse_int(arg[1:]))
                args.remove(arg)
        
        if len(ascensions) == 0:
            ascensions.append(requester_account.get("prestige_level"))

        if len(args) > 0:
            search_value = args[0]
            if utility.contains_ping(search_value):
                search_value = "lifetime_dough"
        else:
            search_value = "lifetime_dough"

        
        search_emoji = values.get_emote_text(search_value)
        if search_emoji is not None:
            search_value = search_emoji
        else:
            pass # search_value is already what we want

        # print(f"Lifetime is {lifetime}, search value is {search_value}")

        if lifetime == False:
            def get_value_of_file(file):
                return file[search_value]
        else: # lifetime is true
            print("lifetime is true so we're using the lifetime function")
            def get_value_of_file(file):
                lifetime_name = "lifetime_" + search_value
                output = 0
                if lifetime_name in file:
                    output += file[lifetime_name]
                    # print(f"adding {file[lifetime_name]} to for lifetime")
                if search_value in file:
                    output += file[search_value]
                    # print(f"adding {file[search_value]} to for current")
                return output

        # TODO: add lifetime_dough_rolled and lifetime_dough_combined
        # thus also dough_rolled and dough_combined

        if search_value.lower() in ["lifetime_dough", "dough_combined", "combined_dough"]:
            def get_value_of_file(file):
                if "earned_dough" in file.keys():
                    dough = file["earned_dough"]
                else:
                    dough = file["lifetime_dough"]
                if "id" in file.keys():
                    portfolio_value = self.get_portfolio_combined_value(file["id"], guild=ctx.guild.id)
                else:
                    portfolio_value = 0

                dough += file.get("gamble_winnings", 0)

                if lifetime is True:
                    if "lifetime_earned_dough" in file.keys():
                        dough += file["lifetime_earned_dough"]
                    if "lifetime_portfolio_value" in file.keys():
                        portfolio_value += file["lifetime_portfolio_value"]
                return dough + portfolio_value
        if search_value.lower() == "stonk_profit":
            def get_value_of_file(file):
                if "id" in file.keys():
                    return self.get_portfolio_combined_value(file["id"], guild=ctx.guild.id)
                else:
                    return 0
        elif search_value.lower() == "portfolio_value":
            def get_value_of_file(file):
                if "id" in file.keys():
                    portfolio_value =  self.get_portfolio_value(file["id"], guild=ctx.guild.id)
                    if (lifetime is True) and ("lifetime_portfolio_value" in file.keys()):
                        portfolio_value += file["lifetime_portfolio_value"]
                    return portfolio_value
                else:
                    return 0
        
        leaderboard = dict()
        total = 0

        all_files = self.json_interface.data[str(ctx.guild.id)]
        
        if search_all is True:
            def include_file(file):
                return True
        else:
            def include_file(file):
                if "id" not in file.keys():
                    return False
                checked_account = self.json_interface.get_account(file["id"], guild = ctx.guild.id)
                if checked_account.get("prestige_level") in ascensions:
                    return True
                else:
                    return False

        for key in all_files.keys():
            if not is_digit(key):
                continue # skip non-numeric keys
            file = all_files[key]
            #print (f"Investigating {key}: \n{file}")
            if search_value in file or search_value in ["portfolio_value", "stonk_profit","lifetime_dough","dough_combined", "combined_dough"]:
                if include_file(file):
                    
                    #list under username then store value for it
                    
                    # leaderboard[file["username"]] = file[search_value]
                    # leaderboard[key] = file[search_value] # instead of the username, index by id
                    file_value = get_value_of_file(file)
                    leaderboard[key] = file_value
                    total += file_value

        # print the leaderboard for testing purposes
        # for key in leaderboard.keys():
            # print(f"{key} has {leaderboard[key]}")

        sorted_ids = sorted(leaderboard, key=leaderboard.get, reverse=True)
        #top_ten = sorted_names[:10]
        #sorted(A, key=A.get, reverse=True)[:5]
        try: 
            person_position = sorted_ids.index(str(person.id)) # zero justified
        except:
            person_position = -1 # not on the board

        top_width = 10
        if wide_leaderboard is True:
            top_width = 20
        side_width = 4
        if wide_leaderboard is True:
            side_width = 7

        starting_range = max(0, person_position - side_width)
        ending_range = min(len(sorted_ids)-1, person_position + side_width)
        top_entries_to_display = min(top_width, len(sorted_ids))
        # print(F"Person index is {person_position}, starting range is {starting_range}, end of range is {ending_range}, len is {len(sorted_names)}")


        output = f"Leaderboard for {search_value}:\n\n"

        output += f"The combined amount between all people is {utility.smart_number(total)}.\n\n"

        # escape_transform = str.maketrans({"_":  r"\_"}) # lol trans

        for index in range(0,top_entries_to_display):
            # name = sorted_names[index]
            id = sorted_ids[index]
            name = self.json_interface.get_account(id, ctx.guild.id).get_display_name()
            output_name = name # the output from get_display_name is escaped
            # output_name = name.translate(escape_transform)
            if index == person_position:
                #bold the user's name
                output += f"{index+1}. **{output_name}: {utility.smart_number(leaderboard[id])}**\n"
            else:
                #don't bold anyone else's name
                output += f"{index+1}. {output_name}: {utility.smart_number(leaderboard[id])}\n"

            if len(output) > 1900:
                # print (f"output is {len(output)} long")
                await ctx.send(output)
                output = "Leaderboard continued:\n\n"
            

        if starting_range > top_entries_to_display:
            output += "\n" # add spacer
        for index in range(starting_range, ending_range+1):
            if index > top_entries_to_display-1:
                # name = sorted_names[index]
                # output_name = name.translate(escape_transform)
                id = sorted_ids[index]
                name = self.json_interface.get_account(id, ctx.guild.id).get_display_name()
                output_name = name
                if index == person_position:
                    #bold the user's name
                    output += f"{index+1}. **{output_name}: {utility.smart_number(leaderboard[id])}**\n"
                else:
                    #don't bold anyone else's name
                    output += f"{index+1}. {output_name}: {utility.smart_number(leaderboard[id])}\n"
                
                if len(output) > 1900:
                    # print (f"output is {len(output)} long")
                    await ctx.send(output)
                    output = "Leaderboard continued:\n\n"

        # print (f"person position is {person_position}")

        person_display_name = self.json_interface.get_account(person.id, ctx.guild.id).get_display_name()

        if person_position != -1: #if they're actually on the list
            output += f"\n{person_display_name} is at position {person_position+1}."

        await ctx.send(output)
        #await ctx.reply("This doesn't actually do anything yet.")


    ########################################################################################################################
    #####      BREAD BLACK_HOLE

    @bread.command(
        hidden = False,
        brief = "Interacts with the black hole technology.",
        help = 
        """
        Usage: 
        $bread black_hole [on/off]
        $bread black_hole [item1] [item2]...
        $bread black_hole show
        
        Use "$bread black_hole" without any arguments or "$bread black_hole [on/off]" to toggle the state of the black hole.
        You can customize what items can be shown in your rolls by appending item names, categories, "14+" or "lottery_win" after the command.
        """,
        aliases = ["blackhole"]
    )
    async def black_hole(self, ctx,
            state: typing.Optional[bool] = commands.parameter(description = "Whether to turn the black hole 'on' or 'off'."), 
            *, args: typing.Optional[str] = commands.parameter(description = "A list of items to show in the black hole.")
            ):
        # booleans here allow converting from "on" and "off" to True and False, neat!

        user_account = self.json_interface.get_account(ctx.author, guild=ctx.guild.id)
        black_hole_value = user_account.get("black_hole")

        if black_hole_value <= 0:
            await ctx.reply("You don't currently possess Black Hole Technology.")
            return

        if args is None:
            if state is None:
                if black_hole_value == 1:
                    user_account.set("black_hole", 2)
                elif black_hole_value == 2:
                    user_account.set("black_hole", 1)
            elif state == True:
                user_account.set("black_hole", 2)
            elif state == False:
                user_account.set("black_hole", 1)

            if user_account.get("black_hole") == 2:
                await ctx.reply("Black hole enabled.")
            elif user_account.get("black_hole") == 1:
                await ctx.reply("Black hole disabled.")

        # check if arg is "show"
        elif len(args) >= 4 and args[:4].lower() == "show":
            # print("showing black hole")
            conditions = user_account.get("black_hole_conditions")
            if len(conditions) == 0:
                await ctx.reply("Your black hole is currently set to show no items.")
            else:
                await ctx.reply("Your black hole is currently set to show: " + " ".join(conditions))

        else:
            conditions = set()
            for arg in args.split(" "):
                # checks if arg is a category
                # from account.get_category

                category = False
                for category_name in [arg, arg[:-1], arg + "s"]:
                    for item in values.all_emotes:
                        if category_name.lower() in item.attributes:
                            conditions.add(item.text)
                            category = True

                # nope, not a category!
                if category is False:
                    if arg == "14+":
                        conditions.add(arg)
                    elif arg == "lottery_win":
                        conditions.add(arg)
                    elif values.get_emote_text(arg) != None:
                        conditions.add(values.get_emote_text(arg))
            
            if len(conditions) == 0:
                await ctx.reply("I could not recognize any item. Your black hole customization has not been changed.")
            else:
                user_account.set("black_hole_conditions", list(conditions))
                await ctx.reply("Your black hole customization has been changed to: " + " ".join(conditions))
        
        # set the account
        self.json_interface.set_account(ctx.author, user_account, ctx.guild.id)


    ########################################################################################################################
    #####      BREAD MUTLIROLLER

    @bread.command(
        name = "multiroller",
        brief = "Modify your Multiroller Terminal settings.",
        description = "Modify your Multiroller Terminal settings.",
        aliases = ["multiroller_terminal"]
    )
    async def multiroller(self, ctx,
            setting: typing.Optional[str] = commands.parameter(description = "The number of multirollers to set as active, or 'off'.")
        ):
        user_account = self.json_interface.get_account(ctx.author.id, ctx.guild.id)

        if user_account.get("multiroller_terminal") == 0:
            await ctx.reply("You do not yet possess the Multiroller Terminal.")
            return

        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Thank you for trying to use the Multiroller Terminal, please move to {self.json_interface.get_rolling_channel(ctx.guild.id)} for configuring the terminal.")
            return
        
        if setting is None:
            await ctx.reply("Please provide a Multiroller Terminal setting.\nEither a number of active Multirollers to set or 'off' to shutdown the terminal and use the maximum possible.")
            return
        
        if setting == "off":
            user_account.set("active_multirollers", -1)

            self.json_interface.set_account(ctx.author.id, user_account, ctx.guild.id)

            await ctx.reply("The Multiroller Terminal has been turned off.")
            return
        
        try:
            setting = parse_int(setting)
        except:
            await ctx.reply("I do not recognize that setting, the Multiroller Terminal settings have not been changed.")
            return
        
        if setting < 0:
            await ctx.reply("You cannot set a negative number of Multirollers to be active.")
            return
        
        if setting > user_account.get("multiroller"):
            await ctx.reply("You cannot have a number of active Multirollers that is greater than the number of Multirollers you have.")
            return
        
        user_account.set("active_multirollers", setting)

        self.json_interface.set_account(ctx.author.id, user_account, ctx.guild.id)

        await ctx.reply(f"You have set the number of active Multirollers to {setting} ({2 ** setting} rolls.)")
        return
        


        


    ########################################################################################################################
    #####      BREAD ROLL NEW

    @bread.command(
        hidden= False,
        brief="A tasty bread roll.",
    )
    async def roll(self, ctx):

        #check if they're already rolling
        if ctx.author.id in self.currently_interacting:
            return
        #otherwise we add them to the list
        self.currently_interacting.append(ctx.author.id)

        user_account = self.json_interface.get_account(ctx.author, guild=ctx.guild.id)
        if not user_account.boolean_is("allowed", default=True):
            await ctx.reply("Sorry, you are not allowed to roll.")
            self.remove_from_interacting(ctx.author.id)
            return

        

        # if user_account.has("daily_rolls", user_account.get("max_daily_rolls")) and ctx.channel.name in earnable_channels:
        #     await ctx.reply("Sorry, but that's all the rolls you can do here for today. New rolls are available each day at <t:1653429922:t>.")
        #     return
        
        user_luck = user_account.get("loaf_converter") + 1
        
        roll_multiplier = 1
        if user_account.get_ephemeral_upgrade(store.Pathfinder.name):
            roll_multiplier = 2
        
        rolls_remaining = (user_account.get("max_daily_rolls") * roll_multiplier) - user_account.get("daily_rolls")
        #if ctx.channel.name in earnable_channels:
        if get_channel_permission_level(ctx) == PERMISSION_LEVEL_MAX:
            multirollers = user_account.get_active_multirollers()
            user_multiroll = 2 ** (multirollers) # 2 to power of multiroller
            user_multiroll = min(user_multiroll, rolls_remaining) 
            # kick user out if they're out of rolls
            if rolls_remaining == 0:
                await ctx.reply( "Sorry, but that's all the rolls you can do here for today. New rolls are available each day at <t:1653429922:t>.")
                self.remove_from_interacting(ctx.author.id)
                return
        else:
            user_multiroll = 1

        #for stored rolls, they are any amount of daily rolls below zero
        # so we get our daily rolls and add our user_multiroll to it
        # and then we check if it's less than zero
        stored_rolls_remaining = -(user_account.get("daily_rolls") + user_multiroll)
        if stored_rolls_remaining < 0:
            stored_rolls_remaining = 0
        
        before_buyable = self.get_buyable_items(user_account, store.all_store_items)
        
        ######
        ############################################################

        result = rolls.bread_roll(
            roll_luck= user_luck, 
            roll_count= user_multiroll,
            user_account=user_account,
            json_interface=self.json_interface
        )

        ############################################################
        ######


        ###########################################################################
        # now we make sure that it's a place they're allowed to roll
        record = False
        allowed_commentary = None

        #check if it's their first ever roll
        if user_account.get("total_rolls") == 0 and get_channel_permission_level(ctx) < PERMISSION_LEVEL_MAX:
            record = True
            allowed_commentary = f"Thank you for rolling some bread! Just a note, please move any future rolls over to {self.json_interface.get_rolling_channel(ctx.guild.id)}."
        
         #check if it's just not a place to roll at all. We'll give first-timers a pass.
        elif get_channel_permission_level(ctx) == PERMISSION_LEVEL_NONE:
            await ctx.reply(f"Sorry, but you cannot roll bread here. Feel free to do so in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            self.remove_from_interacting(ctx.author.id)
            return
        
        #can be rolled but not recorded
        elif get_channel_permission_level(ctx) < PERMISSION_LEVEL_MAX:
            if user_account.get("daily_rolls") <= 0:
                allowed_commentary = f"Thank you for rolling. Remember, any new rolls will only be saved in {self.json_interface.get_rolling_channel(ctx.guild.id)}."
                record = True
            else:
                allowed_commentary = f"Thank you for rolling. Remember, stats are only saved in {self.json_interface.get_rolling_channel(ctx.guild.id)}."
                record = False

        #can be rolled plenty
        elif get_channel_permission_level(ctx) == PERMISSION_LEVEL_MAX:

            record = True
        
        # in neutral land -- NOTE-May not be reached
        else:
            if user_account.get("daily_rolls") == 0:
                allowed_commentary = f"Thank you for rolling. Please remember to roll in {self.json_interface.get_rolling_channel(ctx.guild.id)}."
                record = True
            else:
                await ctx.reply(f"Sorry, you can't roll here. Feel free to do so in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
                self.remove_from_interacting(ctx.author.id)
                return

        ###########################################################################

        count_commentary = None

        # check how many rolls we have left, reject if none remain
        if get_channel_permission_level(ctx) == PERMISSION_LEVEL_MAX:
            amount_remaining = rolls_remaining - user_multiroll
            # amount_remaining =  user_account.get("max_daily_rolls") - user_account.get("daily_rolls")
            if amount_remaining < 0:
                await ctx.reply( "Sorry, but that's all the rolls you can do here for today. New rolls are available each day at <t:1653429922:t>.")
                self.remove_from_interacting(ctx.author.id)
                return
            # we tell them how many stored rolls they have left
            elif stored_rolls_remaining > 0:
                count_commentary = f"You have {utility.smart_number(stored_rolls_remaining)} stored rolls and a total of {utility.smart_number(amount_remaining)} more rolls today."
            #we remove 1 because this check happens *before* the increment, but talks about what happens *after* the increment.

            elif amount_remaining == 0:
                count_commentary = f"That was your last roll for the day."
                # add a special message for new players
                if user_account.get("max_daily_rolls") == 10:
                    count_commentary += '\n\nWould you like to stop by the shop and see what you can get? Check it out with "$bread shop".'
            elif amount_remaining == 1:
                count_commentary = f"You have one more roll today."
            elif amount_remaining <= 3 or user_account.get('roll_summarizer') == 1:
                count_commentary = f"You have {amount_remaining} more rolls today."

        ###########################################################################
        #now we record the roll
        
        summarizer_commentary = None

        if record:

            first_catch_remaining = user_account.get("first_catch_remaining")
            result["value"] = 0

            # save the stats
            for key in result.keys():
                if key not in ["commentary", "emote_text", "highest_roll", "roll_messages", "value", "individual_values", "first_catch_found"]:
                    # this will increase lifetime dough, total dough, and any special values
                    user_account.increment(key,result[key])

                    # #first catch boost
                    # if first_catch_remaining > 0 and key != values.normal_bread.text and key != values.corrupted_bread.text:
                    #     emote = values.get_emote(key)
                    #     if emote is not None:
                    #         new_value = (emote.value + user_account.get_dough_boost_for_item(emote)) * 3
                    #         if result.get("gambit_shop_bonus", 0) > 0:
                    #             result["gambit_shop_bonus"] += user_account.get_dough_boost_for_item(emote) * 3
                    #         # new_value = min(new_value, 100)
                    #         result["value"] += user_account.add_dough_intelligent(new_value)
                    #         first_catch_remaining -= 1
                    #         print(f"first catch remaining: {first_catch_remaining}, emote: {emote.name}")
            
            for item, value in result.get("first_catch_found", []):
                result["value"] += user_account.add_dough_intelligent(value)
                first_catch_remaining -= 1

                print(f"first catch remaining: {first_catch_remaining}, emote: {item.name}")
                            
            user_account.set("first_catch_remaining", first_catch_remaining)
            
            # update the values in the account
            user_account.increment("daily_rolls", user_multiroll)
            user_account.increment("total_rolls", user_multiroll)

            total_value = 0
            for individual_value in result["individual_values"]:
                total_value += user_account.add_dough_intelligent(individual_value)
            #value = user_account.add_dough_intelligent(result["value"])
            result["value"] += total_value # this is for the summarizer
            
            if "gambit_shop_bonus" in result:
                result["gambit_shop_bonus"] *= user_account.get_prestige_multiplier()
                result["gambit_shop_bonus"] = int(result["gambit_shop_bonus"])

            #track highest roll separately
            prev_highest_roll = user_account.get("highest_roll")
            if "highest_roll" in result.keys():
                if result["highest_roll"] > prev_highest_roll:
                    user_account.set_value("highest_roll", result["highest_roll"])
                
            self.json_interface.set_account(ctx.author,user_account, guild = ctx.guild.id)

            if get_channel_permission_level(ctx) == PERMISSION_LEVEL_MAX and user_account.has("roll_summarizer"):
                summarizer_commentary = rolls.summarize_roll(result, user_account)
            

            print (f"{ctx.author.name} rolled {total_value} dough.")

        compound_rolls = 2 ** user_account.get("compound_roller")
        #compound_rolls = 100

        roll_messages = result["roll_messages"]

        # if black hole is active
        if user_account.get("black_hole") == 2 and get_channel_permission_level(ctx) == PERMISSION_LEVEL_MAX:
            # we clear out any "unimportant" rolls
            new_roll_messages = []
            conditions = user_account.get("black_hole_conditions")
            for message in roll_messages:
                if any(item in message for item in conditions) or \
                   (("14+" in conditions) and len(message.split()) >= 14 and len(message.split()) < 50) or \
                   ((("lottery_win" in conditions) or (":fingers_crossed:" in conditions)) and len(message.split()) >= 50):
                    new_roll_messages.append(message)
            roll_messages = new_roll_messages


        # for a non-compound roll, the output is just the input
        if compound_rolls == 1:
            output_messages = roll_messages

        # for a compound roll, we start building the messages up into groups
        elif compound_rolls > 1:
            output_messages = []

            # for as long as we have messages to output
            while len(roll_messages) > 0:
                compound_message = ""
                for i in range(compound_rolls):
                    if len(roll_messages) > 0:
                        potential_addition = roll_messages.pop()

                        # check to make sure we don't hit the length limit
                        if len(compound_message) + len(potential_addition) > 1990:
                            # put it back on the list if it would be too long
                            roll_messages.append(potential_addition)
                            continue

                        compound_message += potential_addition

                        # if there's still messages left, add a space
                        if len(roll_messages) > 0:
                            #if len(compound_message) + len (roll_messages[-1]) < 1900: #getting at -1 is peek function
                            if i < compound_rolls - 1: # if there's still space to go
                                compound_message += "\n---\n"
                output_messages.append(compound_message)
            
        # check if black hole is activated and if we're in #bread-rolls
        if user_account.get("black_hole") == 2 and get_channel_permission_level(ctx) == PERMISSION_LEVEL_MAX:
            await ctx.reply(":cyclone:")
        
        # black hole is not activated, send messages normally
        for roll in output_messages:
            await ctx.reply(roll)
            if len(output_messages) > 1:
                await asyncio.sleep(.75)
                
        output_commentary = ""

        roll_commentary = result["commentary"]
        if roll_commentary is not None:
            
            output_commentary += roll_commentary

        #add the last bit on
        if allowed_commentary is not None:
            output_commentary += "\n\n" + allowed_commentary


        if count_commentary is not None:
            output_commentary += "\n\n" + count_commentary

        if summarizer_commentary is not None:
            output_commentary += "\n\n" + summarizer_commentary
        
        after_buyable = self.get_buyable_items(user_account, store.all_store_items)
        output_commentary += self.describe_added_shop_items(before_buyable, after_buyable)

        try:
            if output_commentary != "" and not output_commentary.isspace():
                messages = [output_commentary]
                if len(output_commentary) > 1900:
                    messages = []
                    split = output_commentary.split("\n")

                    add = []

                    for split_item in split:
                        if len("\n".join(add + [split_item])) > 1900:
                            messages.append("\n".join(add))
                            add = ["Summary continued:", split_item]
                        else:
                            add.append(split_item)
                    
                    if len(add) > 0:
                        messages.append("\n".join(add))
                
                for message in messages:
                    await ctx.reply(message)
                
        except:
            print(traceback.format_exc())

        await self.do_chessboard_completion(ctx)
        await self.anarchy_chessatron_completion(ctx)

        # self.json_interface.set_account(ctx.author, user_account, ctx.guild.id)

        #now we remove them from the list of rollers, this allows them to roll again without spamming
        self.remove_from_interacting(ctx.author.id)

    ########################################################################################################################
    #####      do CHESSBOARD COMPLETION

    async def do_chessboard_completion(
            self: typing.Self,
            ctx: commands.Context,
            force: bool = False,
            amount: int = None
        ) -> None:
        """Runs the chessatron creation animation, as well as making the chessatrons themselves.

        Args:
            ctx (commands.Context): The context the chessatron creation was invoked in.
            force (bool, optional): Whether to override `auto_chessatron`. Defaults to False.
            amount (int, optional): The amount of chessatrons to make. Will make as many as possible if None is provided. Defaults to None.
        """

        user_account = self.json_interface.get_account(ctx.author, guild=ctx.guild.id)

        if user_account.get("auto_chessatron") is False and force is False:
            return
        
        # print ("doing chessatron creation")

        # user_chess_pieces = user_account.get_all_items_with_attribute_unrolled("chess_pieces")
        full_chess_set = values.chess_pieces_black_biased+values.chess_pieces_white_biased

        # leftover_pieces = utility.array_subtract((full_chess_set), user_chess_pieces )
        #print(f"{ctx.author} has {len(leftover_pieces)} pieces left to collect.")
        #print(f"Those pieces are: {leftover_pieces}")


        # pointwise integer division between the full chess set and the set of the user's pieces.
        valid_trons = min([user_account.get(x.text) // full_chess_set.count(x) for x in values.all_chess_pieces])

        # iteration ends at the minimum value, make sure amount is never the minimum. 'amount is None' should mean no max ...
        # ... has been specified, so make as many trons as possible.
        if amount is None: 
            amount = valid_trons + 1

        # print(f"valid trons: {valid_trons}, amount: {amount}")

        board = self.format_chess_pieces(user_account.values)
        chessatron_value = user_account.get_chessatron_dough_amount(include_prestige_boost=False) 
        trons_to_make = min(valid_trons, amount)

        # for emote in full_chess_set:
        #     user_account.increment(emote.text, -1)

        # clear out the chess pieces from the account all at once
        for chess_piece in full_chess_set:
            user_account.increment(chess_piece, -trons_to_make)

        

        # first we add the dough and attributes
        total_dough_value = user_account.add_dough_intelligent(chessatron_value * trons_to_make)
        user_account.add_item_attributes(values.chessatron, trons_to_make)

        # we save the account
        self.json_interface.set_account(ctx.author, user_account, ctx.guild.id)

        # then we send the tron messages
        if trons_to_make == 0:
            return
        elif not user_account.get("tron_animation"):
            # If the tron animation is disabled run this instead.
            output = f"Congratulations! You have made {utility.write_count(trons_to_make, 'chessatron')}! Here is your reward of **{utility.smart_number(total_dough_value)} dough**.\n\n{values.chessatron.text} x {utility.smart_number(trons_to_make)}"
            await ctx.reply(output)
        elif user_account.get("full_chess_set") <= 5:
            messages_to_send = trons_to_make
            while messages_to_send > 0:
                await ctx.reply(f"You have collected all the chess pieces! Congratulations!\n\nWhat a beautiful collection!")
                await asyncio.sleep(1)

                await ctx.reply(f"{board}")
                await asyncio.sleep(1)

                await ctx.reply(f"You will now be awarded the most prestigious of chess pieces: The Mega Chessatron!")
                await asyncio.sleep(1)

                await ctx.reply(f"{values.chessatron.text}")
                await asyncio.sleep(1)
                await ctx.reply(f"May it serve you well. You also have been awarded **{utility.smart_number(total_dough_value//trons_to_make)} dough** for your efforts.")
                messages_to_send -= 1
        elif trons_to_make < 10:
            messages_to_send = trons_to_make
            while messages_to_send > 0:
                await asyncio.sleep(1)
                await ctx.reply(f"Congratulations! You've collected all the chess pieces! This will be chessatron **#{utility.smart_number(user_account.get('full_chess_set')+1-messages_to_send)}** for you.\n\n{board}\nHere is your award of **{utility.smart_number(total_dough_value//trons_to_make)} dough**, and here's your new chessatron!")
                await asyncio.sleep(1)
                await ctx.reply(f"{values.chessatron.text}")
                messages_to_send -= 1
        elif trons_to_make < 5000:
            output = f"Congratulations! More chessatrons! You've made {utility.smart_number(user_account.get('full_chess_set'))} of them in total and {utility.smart_number(trons_to_make)} right now! Here's your reward of **{utility.smart_number(total_dough_value)} dough**."
            await ctx.reply(output)
            await asyncio.sleep(1)
            
            output = ""
            for _ in range(trons_to_make):
                output += f"{values.chessatron.text} "
                if len(output) > 1800:
                    await ctx.reply(output)
                    output = ""
                    await asyncio.sleep(1)
            await ctx.reply(output)
        else:
            output = f"Wow. You have created a **lot** of chessatrons. {utility.smart_number(trons_to_make)} to be exact. I will not even attempt to list them all. Here is your reward of **{utility.smart_number(total_dough_value)} dough**."
            await ctx.reply(output)
            await asyncio.sleep(1)
            await ctx.reply(f"{values.chessatron.text} x {utility.smart_number(trons_to_make)}")

    

    ########################################################################################################################
    #####      BREAD CHESSATRON

    @bread.command(
        name="chessatron", 
        aliases=["auto_chessatron", "tron"],
        help="Toggle auto chessatron on or off. If no argument is given, it will create as many chessatrons for you as it can.",
        usage="on/off",
        brief="Toggle auto chessatron on or off."
    )
    async def chessatron(self, ctx,
            arg: typing.Optional[str] = commands.parameter(description = "Turn Auto Chessatron 'on' or 'off', or a number to make that many trons.")
            ) -> None:
        """Toggle auto chessatron on or off."""
        
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        if arg is None:
            arg = ""
        
        if arg.lower() == "on":
            user_account.set("auto_chessatron", True)
            self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)
            await ctx.reply(f"Auto chessatron is now on.")
        elif arg.lower() == "off":
            user_account.set("auto_chessatron", False)
            self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)
            await ctx.reply(f"Auto chessatron is now off.")
        else:
            if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
                await ctx.reply(f"Thank you for your interest in creating chessatrons! You can do so over in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
                return
            
            if is_numeric(arg):
                await self.do_chessboard_completion(ctx, True, amount = parse_int(arg))
            else:
                await self.do_chessboard_completion(ctx, True)

    

    ########################################################################################################################
    #####      BREAD TRON_ANIMATION

    @bread.command(
        name="tron_animation", 
        aliases=["chessatron_animation", "animation_tron", "animation_chessatron"],
        help="Toggles the chessatron animation on and off.",
        usage="on/off",
        brief="Toggles the chessatron animation on and off."
    )
    async def tron_animation(self, ctx,
            arg: typing.Optional[str] = commands.parameter(description = "Turn the chessatron animation 'on' or 'off'.")
            ) -> None:
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        if arg is None:
            arg = ""
        
        if arg.lower() == "on":
            do_enable = True
        elif arg.lower() == "off":
            do_enable = False
        else:
            do_enable = not user_account.get("tron_animation")
            
        if do_enable:
            user_account.set("tron_animation", True)
            self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)
            await ctx.reply(f"The chessatron animation is now enabled.")
        else:
            user_account.set("tron_animation", False)
            self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)
            await ctx.reply(f"The chessatron animation is now disabled.")

        

    ########################################################################################################################
    #####      BREAD GEM_CHESSATRON

    @bread.command(
        help = "Create a chessatron from red gems.",
        aliases = ["gem_tron"]
    )
    async def gem_chessatron(self, ctx,
            # arg: typing.Optional[str] = commands.parameter(description = "The number of chessatrons to create.")
            *args
            ):

        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        highest_gem_index = 1
        number_of_chessatrons = None
        emote = values.gem_red.text

        # first get the gem, if applicable
        for arg in args:
            #test if is emoji
            emote = values.get_emote_text(arg)
            if emote is None:
                # make sure it's an emote
                continue

            if emote == values.gem_red.text:
                highest_gem_index = 1
                break
            elif emote == values.gem_blue.text:
                highest_gem_index = 2
                break
            elif emote == values.gem_purple.text:
                highest_gem_index = 3
                break
            elif emote == values.gem_green.text:
                highest_gem_index = 4
                break
            elif emote == values.gem_gold.text:
                highest_gem_index = 5
                break
        
        # then get the count of chessatrons to try to make
        for arg in args:
            if is_numeric(arg):
                number_of_chessatrons = parse_int(arg)
                break
        
        if number_of_chessatrons is not None and number_of_chessatrons < 0:
            await ctx.reply("You can't make a negative number of chessatrons.")
            return
        

        total_gem_count = 0
        red_gems = user_account.get(values.gem_red.text)
        blue_gems = user_account.get(values.gem_blue.text)
        purple_gems = user_account.get(values.gem_purple.text)
        green_gems = user_account.get(values.gem_green.text)
        gold_gems = user_account.get(values.gem_gold.text) * 4


        if highest_gem_index >= 1:
            total_gem_count += red_gems
        if highest_gem_index >= 2:
            total_gem_count += blue_gems
        if highest_gem_index >= 3:
            total_gem_count += purple_gems
        if highest_gem_index >= 4:
            total_gem_count += green_gems
        if highest_gem_index >= 5:
            # 4 gems per gold gem
            total_gem_count += gold_gems
        

        if number_of_chessatrons is None:
            number_of_chessatrons = total_gem_count // 32
        else:
            number_of_chessatrons = min(total_gem_count // 32, number_of_chessatrons)

        
        

        # gem_count = user_account.get(values.gem_red.text)

        if total_gem_count < 32 or number_of_chessatrons == 0:
            await ctx.reply(f"You need at least 32 gems to create a chessatron.")
            return

        gems_needed = number_of_chessatrons * 32

        if gems_needed > red_gems: # if not enough red gems to make all trons
            gems_needed -= red_gems # then use all red gems in our count
            red_gems_used = red_gems # mark that we've used all our red gems
            red_gems = 0
        else: # if enough red gems to make all trons
            red_gems_used = gems_needed # mark that we've used all the red gems we need
            gems_needed = 0
            red_gems -= red_gems_used

        if gems_needed > blue_gems:
            gems_needed -= blue_gems
            blue_gems_used = blue_gems
            blue_gems = 0
        else: # if enough blue gems to make all trons
            blue_gems_used = gems_needed
            gems_needed = 0
            blue_gems -= blue_gems_used
        
        if gems_needed > purple_gems:
            gems_needed -= purple_gems
            purple_gems_used = purple_gems
            purple_gems = 0
        else: # if enough purple gems to make all trons
            purple_gems_used = gems_needed
            gems_needed = 0
            purple_gems -= purple_gems_used

        if gems_needed > green_gems:
            gems_needed -= green_gems
            green_gems_used = green_gems
            green_gems = 0
        else: # if enough green gems to make all trons
            green_gems_used = gems_needed
            gems_needed = 0
            green_gems -= green_gems_used

        if gems_needed > gold_gems:
            gems_needed -= gold_gems
            gold_gems_used = gold_gems
            gold_gems = 0
        else: # if enough gold gems to make all trons
            gold_gems_used = gems_needed
            gems_needed = 0
            gold_gems -= gold_gems_used

        if gems_needed > 0:
            await ctx.reply("It seems something went wrong.")
            return

        if gold_gems // 4 != gold_gems / 4:
            # if we used a fraction of a gold gem
            green_gems += round(((gold_gems / 4) - (gold_gems // 4)) * 4)

        user_account.set(values.gem_red.text, red_gems)
        user_account.set(values.gem_blue.text, blue_gems)
        user_account.set(values.gem_purple.text, purple_gems)
        user_account.set(values.gem_green.text, green_gems)
        user_account.set(values.gem_gold.text, gold_gems // 4)

        # if arg is None:
        #     arg = None
        #     number_of_chessatrons = gem_count // 32 # integer division
        # elif is_numeric(arg):
        #     arg = parse_int(arg)
        #     number_of_chessatrons = min(gem_count // 32,arg) # integer division
        # else:
        #     arg = None
        #     number_of_chessatrons = gem_count // 32 # integer division

        # user_account.increment(values.gem_red.text, -32*number_of_chessatrons)

        user_account.increment(values.black_pawn.text, 8*number_of_chessatrons)
        user_account.increment(values.black_rook.text, 2*number_of_chessatrons)
        user_account.increment(values.black_knight.text, 2*number_of_chessatrons)
        user_account.increment(values.black_bishop.text, 2*number_of_chessatrons)
        user_account.increment(values.black_queen.text, 1*number_of_chessatrons)
        user_account.increment(values.black_king.text, 1*number_of_chessatrons)

        user_account.increment(values.white_pawn.text, 8*number_of_chessatrons)
        user_account.increment(values.white_rook.text, 2*number_of_chessatrons)
        user_account.increment(values.white_knight.text, 2*number_of_chessatrons)
        user_account.increment(values.white_bishop.text, 2*number_of_chessatrons)
        user_account.increment(values.white_queen.text, 1*number_of_chessatrons)
        user_account.increment(values.white_king.text, 1*number_of_chessatrons)

        self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)

        gems_list = []

        if red_gems_used > 0:
            gems_list.append(f"{red_gems_used} {values.gem_red.text}")
        if blue_gems_used > 0:
            gems_list.append(f"{blue_gems_used} {values.gem_blue.text}")
        if purple_gems_used > 0:
            gems_list.append(f"{purple_gems_used} {values.gem_purple.text}")
        if green_gems_used > 0:
            gems_list.append(f"{green_gems_used} {values.gem_green.text}")
        if gold_gems_used > 0:
            gems_list.append(f"{gold_gems_used // 4} {values.gem_gold.text}")

        gems_string = ", ".join(gems_list)

        await ctx.reply(f"You have used {gems_string} to make chess pieces.")

        await self.do_chessboard_completion(ctx, amount = parse_int(number_of_chessatrons))

    ########################################################################################################################
    #####      BREAD SPELLCHECK

    # toggles whether the default of calling bread without arguments is to succeed or not
    @bread.command(
        name="spellcheck", 
        aliases=["spell_check"],
        help="Toggle spellcheck on or off. If no argument is given, it will toggle the current setting.",
        usage="on/off",
        brief="Toggle spellcheck on or off."

    )
    async def spellcheck(self, ctx,
            toggle: typing.Optional[str] = commands.parameter(description = "Whether to turn spellcheck 'on' or 'off'.")
            ):
        """Toggle spellcheck on or off."""

        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        if toggle is None:
            toggle = ""
        
        if toggle.lower() == "on":
            user_account.set("spellcheck", True)
            await ctx.reply(f"Spellcheck is now on.")
        elif toggle.lower() == "off":
            user_account.set("spellcheck", False)
            await ctx.reply(f"Spellcheck is now off.")
        else:
            user_account.set("spellcheck", not user_account.get("spellcheck"))
            if user_account.get("spellcheck"):
                await ctx.reply(f"Spellcheck is now on.")
            else:
                await ctx.reply(f"Spellcheck is now off.")

        self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)


    ########################################################################################################################
    #####      BREAD RESET ACCOUNT

    @bread.command(
        name="reset_account"
    )
    async def bread_reset_accound(self, ctx):
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
        
        await ctx.reply("Are you *sure* you want to reset your account?\nThis cannot be undone, and it will reset *all* of your lifetime stats.\n\nIf you are sure you want to reset your account, please send your Loaf Converter amount.")

        def check(m: discord.Message):  # m = discord.Message.
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
        
        try:
            msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
        except asyncio.TimeoutError: 
            await ctx.reply("You have taken too long to answer, please start over.")
            return 
        
        lc_amount = str(user_account.get(store.Loaf_Converter.name))
        formatted_lc_amount = utility.smart_number(user_account.get(store.Loaf_Converter.name))
        
        if not(msg.content == lc_amount or msg.content == formatted_lc_amount):
            if lc_amount in msg.content or formatted_lc_amount in msg.content:
                await ctx.reply("I can find your Loaf Converter amount in that message, however to be sure you want to reset your account, please start over and send only the amount of Loaf Converters you have, nothing else.")
                return
            await ctx.reply("I cannot find your Loaf Converter amount in your message, please start over.")
            return
        
        file_text = json.dumps(user_account.values, indent=4)

        fake_file = io.StringIO(file_text)
        final_file = discord.File(fake_file, filename="export.json")
        
        # o7
        
        user_account.reset_to_default()
        self.json_interface.set_account(ctx.author.id, user_account, ctx.guild)
        
        await ctx.reply("Success, your account has been reset.\n\nFor archival purposes, here are your stats prior to being reset:", file=final_file)
        


    ########################################################################################################################
    #####      BREAD ASCEND

    @bread.command(
        name="ascend", 
        aliases=["ascension", "rebirth", "prestige"]
    )
    async def ascend(self, ctx):
        """Ascend to a higher plane of existence."""
        
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
        prestige_level = user_account.get_prestige_level()

        prestige_file = self.json_interface.get_custom_file("prestige", guild = ctx.guild.id)
        if "max_prestige_level" in prestige_file:
            max_prestige_level = prestige_file["max_prestige_level"]
        else:
            max_prestige_level = 1

        # max_prestige_level = 3

        ascend_dough_cost = (prestige_level * 250000) # starts at 500k and goes up
        daily_rolls_requirement = 1000 + prestige_level * 100
        
        # if prestige_level >= max_prestige_level:
        #     await ctx.reply(f"You are already at the highest level of ascension which is currently available.")
        #     return

        if user_account.get("max_daily_rolls") < 1000:
            await ctx.reply(f"{utility.smart_number(daily_rolls_requirement)} daily rolls is not the only requirement to ascend, but it is the first one. Come back when you have that many.")
            return

        description = "An **ascension** is a powerful thing. It will reset your progress and you will start over from scratch.\n"
        description += "However, in return, you will recieve a few things:\n\n"
        description += "-You will gain access to a special shop, and to the currency you can spend there.\n"
        description += "-You will have a higher limit for how many daily rolls you can buy.\n"
        description += "-And the dough you roll will be worth more.\n\n"

        description += "**In order to ascend, you need the following:**\n"
        description += f"-{utility.smart_number(daily_rolls_requirement)} daily rolls\n"
        # description += f"-{utility.smart_number(ascend_dough_cost)} dough\n"
        # description += "-A golden gem\n\n"
        description += "-128 loaf converters\n"
        description += "-200 chessatrons\n\n"


        can_ascend = (user_account.get("max_daily_rolls") >= daily_rolls_requirement) and \
                        (user_account.get(values.chessatron.text) >= 200) and \
                        (user_account.get("loaf_converter") >= 128)
                        # (user_account.get(values.gem_gold.text) >= 1)
                        # (user_account.get("total_dough") >= ascend_dough_cost) and \

        if prestige_level >= max_prestige_level:
            description += "**You are already at the highest level of ascension which is currently available.**\n\n"
            await ctx.reply(description)
            return

        if not can_ascend:
            description += "\n**You cannot ascend yet.**\n\n"
            await ctx.reply(description)
            return
        else:
            description += "\n**You can ascend!**\n\n"

        description += """If you would like to ascend, please type "I would like to ascend".\nIf you would like to ascend to the highest available ascension, please type "Take me to the latest ascension".\nRemember that this is a permanent action that cannot be undone."""

        await ctx.reply(description)

        def check(m: discord.Message):  # m = discord.Message.
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id 
        try:
            msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
        except asyncio.TimeoutError: 
            await ctx.reply("If you are not ready yet, that is okay.")
            return 
        
        response = msg.content
        next_ascension_msg = "i would like to ascend" in response.lower()
        latest_ascension_msg = "take me to the latest ascension" in response.lower()

        if next_ascension_msg and latest_ascension_msg:
            await ctx.reply("Contradictory messages, I see. Please come back when you are feeling more decisive.")
            return
        elif next_ascension_msg:
            # now we can ascend
            #user_account.increment(values.gem_gold.text, -1) # first remove the golden gem
            user_account.increase_prestige_level()

            description = f"Congratulations! You have ascended to a higher plane of existence. You are now at level {user_account.get_prestige_level()} of ascension. I wish you the best of luck on your journey!\n\n"
            description += f"You have also recieved **1 {values.ascension_token.text}**. You will recieve more as you get more daily rolls. You can spend it at the hidden bakery to buy special upgrades. Find it with \"$bread hidden_bakery\"."
            await ctx.reply(description)
        elif latest_ascension_msg:
            pre_ascension_tokens = user_account.get(values.ascension_token.text)
            user_account.increase_prestige_to_goal(max_prestige_level)
            post_ascension_tokens = user_account.get(values.ascension_token.text)

            description = f"Congratulations! You have ascended to the highest plane of existence. You are now at level {user_account.get_prestige_level()} of ascension. I wish you the best of luck on your journey!\n\n"
            description += f"You have also recieved **{post_ascension_tokens - pre_ascension_tokens} {values.ascension_token.text}**. You will recieve more as you get more daily rolls. You can spend it at the hidden bakery to buy special upgrades. Find it with \"$bread hidden_bakery\"."
            await ctx.reply(description)
        else:
            await ctx.reply("If you are not ready yet, that is okay.")
            return 

        # and save the account
        self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)
        
    ########################################################################################################################
    #####      SHOP HELPER
    
    async def shop_helper(
            self: typing.Self,
            ctx: commands.Context | utility.CustomContext,
            user_account: account.Bread_Account,
            buyable_list: list[type[store.Store_Item]],
            shop_name: str,
            prefix: str = None,
            suffix: str = None,
            suffix_line_break: bool = True
        ) -> discord.Message:
        """Helper method to run every shop in the game.
        This handles the generation of the message content, as well as the actual sending of the message itself.
        This does mean that the shops are standardized.

        Args:
            ctx (commands.Context | utility.CustomContext): The discord.py context.
            user_account (account.Bread_Account): The user account of the user requesting the shop.
            buyable_list (list[type[store.Store_Item]]): The list of items that will populate this shop.
            shop_name (str): The name of the shop, to be inserted at the start of the message.
            prefix (str, optional): A prefix to put directly after the shop introduction. Defaults to None.
            suffix (str, optional): A suffix to put at the end of the message. Defaults to None.
            suffix_line_break (bool, optional): Whether to add a line break between the "To buy an item, just type "$bread buy [item name]"." message and the suffix. This does nothing if the suffix is None. Defaults to None.

        Returns:
            discord.Message: The sent message.
        """

        # now we get the list of items
        items = self.get_buyable_items(user_account, buyable_list)

        # Get list of non-purchasable items.
        purchasable_set = set(items)
        item_list = buyable_list
        non_purchasable_items = set(item_list) - purchasable_set # type: set[store.Salvage_Shop_Item]

        output = ""
        if prefix:
            prefix = f"\n{prefix}"
        else:
            prefix = ""
        output += f"Welcome to the {shop_name}!{prefix}\nHere are the items available for purchase:\n\n"

        displayed_items = 0
        
        # The length of the "you've already bought everything here" message is 59, but I rounded it up to 65 just to be careful.
        output_suffix_length = 65 + (len(suffix) if suffix else 0)

        for item in item_list:
            requirement_given = False
            requirement = None

            if item in non_purchasable_items:
                try:
                    if user_account.get(item.name) >= item.max_level(user_account):
                        continue
                except TypeError:
                    # If the output from item.max_level is None then a TypeError will be raised.
                    pass

                requirement = item.get_requirement(user_account)

                if requirement is None:
                    continue    

                requirement_given = True
                

            if item in purchasable_set or requirement_given:
                old_output = output

                add = ""

                add += f"\t**{item.display_name}** - {item.get_price_description(user_account)}\n{item.description(user_account)}\n"

                if requirement_given:
                    add += f"*Not purchasable right now. {requirement}*\n"
                    
                add += "\n"

                displayed_items += 1

                output += add

                if len(output) + output_suffix_length > 1900:
                    await ctx.reply(old_output)
                    output = f"Continued shop:\n\n{add}"
        
        if displayed_items == 0:
            output += "**It looks like you've bought everything here. Well done.**"
        else:
            output += 'To buy an item, just type "$bread buy [item name]".'
            
        if suffix:
            output += "\n" + ('\n' if suffix_line_break else '') + suffix

        return await ctx.reply(output)
        

    ########################################################################################################################
    #####      BREAD SHOP / BREAD STORE

    #this one, we'll have display the available items, and have the "buy" function actually purchase them
    @bread.command(
        hidden=False,
        aliases=["store"],
        brief= "Spend your hard-earned dough.",
        help = "Shows what's available to purchase.\n\nUse '$bread buy <item>' to buy an item from the store.\n\nOnly works in #bread-rolls."
    )
    async def shop(self, ctx):

        # first we make sure this is a valid channel
        #if ctx.channel.name not in earnable_channels:
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Hi! Thanks for visiting the bread shop. Our nearest location is over in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        # we get the account of the user who called it
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
        
        suffix = "Don't forget to check out the **gambit shop**. Find it with \"$bread gambit_shop\"." #

        if user_account.get_prestige_level() >= 1:
            suffix += "\nYou can also buy items from the **hidden bakery**. Find it with \"$bread hidden_bakery\"."
            suffix += "\nYou're also able to purchase stuff from the **space shop**. Find it with \"$bread space shop\"."
        
        await self.shop_helper(
            ctx = ctx,
            user_account = user_account,
            buyable_list = store.normal_store_items,
            shop_name = "the store",
            prefix = f"You have **{utility.smart_number(user_account.get('total_dough'))} dough**.\n\*Prices subject to change.",
            suffix = suffix
        )

    ########################################################################################################################
    #####      BREAD ASCENSION_SHOP / BREAD HIDDEN_BAKERY

    #this is the shop for the ascension items, and can only be accessed once a user has at least 1 prestige
    @bread.command(
        aliases = ["hidden", "secret_shop", "ascension_shop"],
        brief = "Spend your ascension tokens.",
    )
    async def hidden_bakery(self, ctx):
            
        # first we make sure this is a valid channel
        #if ctx.channel.name not in earnable_channels:
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Hi! Thanks for visiting the hidden bakery. You can find us in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        # we get the account of the user who called it
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        if user_account.get_prestige_level() < 1:
            await ctx.reply("The door to this shop seems to be locked.")
            return
        
    
        await self.shop_helper(
            ctx = ctx,
            user_account = user_account,
            buyable_list = store.prestige_store_items,
            shop_name = "Hidden Bakery",
            prefix = f"All upgrades in this shop are permanent, and persist through ascensions. You have **{utility.smart_number(user_account.get(values.ascension_token.text))} {values.ascension_token.text}**."
        )

    ########################################################################################################################
    #####      BREAD GAMBIT_SHOP

    # this is the gambit shop, which can be accessed at any point
    @bread.command(
        aliases = ["strategy_store", "strategy_shop", "gambit", "strategy"],
        brief = "Fine tune your strategies.",
        description = "Fine tune your strategies."
    )
    async def gambit_shop(self, ctx):
        
        # first we make sure this is a valid channel
        #if ctx.channel.name not in earnable_channels:
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Hi! Thanks for visiting the gambit shop. Our nearest location is over in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        # we get the account of the user who called it
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
        
        await self.shop_helper(
            ctx = ctx,
            user_account = user_account,
            buyable_list = store.gambit_shop_items,
            shop_name = "Gambit Shop"
        )

    ########################################################################################################################
    #####      BREAD BUY
    
    async def buy_confirmation_catalyst(
            self: typing.Self,
            ctx: commands.Context | utility.CustomContext,
            user_account: account.Bread_Account,
            item: type[store.Store_Item]
        ) -> bool:
        """Purchase confirmation for catalysts.

        Args:
            ctx (commands.Context | utility.CustomContext): The command context.
            user_account (account.Bread_Account): The user running the command.
            item (type[store.Store_Item]): The item to be purchased.

        Returns:
            bool: Whether to allow the purchase to complete.
        """
        active = store.find_catalyst(user_account.get("active_catalyst"))
        remaining = user_account.get("catalyst_remaining")
        
        if active is None:
            return True
        
        if remaining <= 0:
            return True
        
        if ctx.author.id in self.currently_interacting:
            return False
        
        # If it gets here we need to prompt the user to make sure they
        # want to overwrite their existing catalyst with the new one.
        
        def check(m: discord.Message):  # m = discord.Message.
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
        
        await ctx.reply(f"You already have a catalyst active, **{active.display_name}**, with **{utility.write_count(remaining, 'salvage')}** remaining."
                        f"\nAre you sure you want to purchase the **{item.display_name}** catalyst and overwrite your existing one? Yes or no.")
        
        self.currently_interacting.append(ctx.author.id)
        
        try:
            msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
        except asyncio.TimeoutError: 
            await ctx.reply("I'm sorry, but you have taken too long to answer and I must attend to the next customer.")
            self.remove_from_interacting(ctx.author.id)
            return False
                
        confirm_text = ["yes", "y", "confirm"]
        cancel_text = ["no", "n", "cancel"]
                
        if msg.content.lower() in cancel_text:
            await ctx.reply("Very well, come back when you would like to purchase a Catalyst.")

            self.remove_from_interacting(ctx.author.id)
            return False
        elif msg.content.lower() not in confirm_text:
            await ctx.reply("I'm not entirely sure what that is, please try again.")

            self.remove_from_interacting(ctx.author.id)
            return False
        
        self.remove_from_interacting(ctx.author.id)
        
        return True
        
    ##############################################################################
    
    async def buy_confirmation_ephemeral(
            self: typing.Self,
            ctx: commands.Context | utility.CustomContext,
            user_account: account.Bread_Account,
            item: type[store.Store_Item]
        ) -> bool:
        """Purchase confirmation for ephemeral upgrades.

        Args:
            ctx (commands.Context | utility.CustomContext): The command context.
            user_account (account.Bread_Account): The user running the command.
            item (type[store.Store_Item]): The item to be purchased.

        Returns:
            bool: Whether to allow the purchase to complete.
        """
        max_amount = user_account.get_max_ephemeral_count()
        upgrade_file = user_account.get_ephemeral_file()
        
        if len(upgrade_file) < max_amount:
            return True

        if ctx.author.id in self.currently_interacting:
            return False
        
        if item.name in upgrade_file:
            await ctx.reply("You already have that Ephemeral Upgrade purchased.")
            return False
        
        def check(m: discord.Message):  # m = discord.Message.
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
        
        await ctx.reply(self.get_active_ephemeral_list(user_account) \
            + f"\nPurchasing the **{item.display_name}** Ephemeral Upgrade will replace **{store.find_ephemeral_upgrade(upgrade_file[-1]).display_name}**." \
            + "\nAre you sure you want to continue? Yes or no." \
            + ("\n*You can cancel an upgrade you currently have with '$bread ephemeral cancel [upgrade name]'*" if max_amount >= 2 else ""))
        
        self.currently_interacting.append(ctx.author.id)
        
        try:
            msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
        except asyncio.TimeoutError: 
            await ctx.reply("I'm sorry, but you have taken too long to answer and I must attend to the next customer.")
            self.remove_from_interacting(ctx.author.id)
            return False
                
        confirm_text = ["yes", "y", "confirm"]
        cancel_text = ["no", "n", "cancel"]
                
        if msg.content.lower() in cancel_text:
            await ctx.reply("Very well, come back when you would like to purchase an Ephemeral Upgrade.")

            self.remove_from_interacting(ctx.author.id)
            return False
        elif msg.content.lower() not in confirm_text:
            await ctx.reply("I'm not entirely sure what that is, please try again.")

            self.remove_from_interacting(ctx.author.id)
            return False
        
        self.remove_from_interacting(ctx.author.id)
        
        return True
        
    ##############################################################################

    # this lets us purchase items we see in the store
    @bread.command(
        hidden=False,
        aliases=["purchase"],
        help= "Usage: $bread buy [item name]\n\nBuys an item from the bread store. Only works in #bread-rolls.",
        brief= "Buy an item from the bread shop.",
    )
    async def buy(self, ctx,
            *, item_name: typing.Optional[str] = commands.parameter(description = "The item you would like to purchase.")
            ):

        if item_name is None:
            await ctx.reply("Please specify an item to buy.")
            return

        # first we make sure this is a valid channel
        #if ctx.channel.name not in earnable_channels:
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Thank you for your interest in purchasing an item from the store. Please visit our nearby location in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return

        # split the first word of the item name and check if it's a number
        item_count = 1
        item_name_split = item_name.split(" ")
        if len(item_name_split) > 1:
            if item_name_split[0][0] == '-':
                await ctx.reply("You can't buy negative numbers of items.")
                return
            if is_digit(item_name_split[0]):
                item_name = " ".join(item_name_split[1:])
                item_count = parse_int(item_name_split[0])
            if item_name_split[0] == "all":
                item_name = " ".join(item_name_split[1:])
                item_count = 100000

        # remove trailing 's' from the item name
        if len(item_name) > 1 and item_name[-1] == "s":
            item_name_2 = item_name[:-1]
        else:
            item_name_2 = item_name

        if item_count < 1:
            await ctx.reply("You can't buy zero of an item.")
            return

        # first we get the account of the user who called it
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        # now we get the list of items
        if user_account.get_prestige_level() < 1:
            buyable_items = self.get_buyable_items(user_account, store.normal_store_items)
            buyable_items.extend(self.get_buyable_items(user_account, store.gambit_shop_items))
        else: # has achieved a prestige level
            buyable_items = self.get_buyable_items(user_account, store.all_store_items)
        all_items = store.all_store_items


        # now we check if the item is in the list

        item_name = item_name.lower()

        item = None
        for i in all_items:
            if i.name.lower() == item_name or i.display_name.lower() == item_name:
                item = i
                break
            # this is for the item's name minus a trailing "s"
            if i.name.lower() == item_name_2 or i.display_name.lower() == item_name_2:
                item = i
                break
            # this is for aliases
            aliases = [option.lower() for option in i.aliases]
            if item_name in aliases or item_name_2 in aliases:
                item = i
                break
        else: # if the for loop doesn't break, run this. This should run the same as an 'if item is None' check.
            await ctx.reply("Sorry, but I don't recognize that item's name.")
            return


        def describe_cost(item_text):
            amount = user_account.get(item_text)
            if item_text == "total_dough":
                return f"**{utility.smart_number(amount)} dough**"
            else:
                return f"**{utility.smart_number(amount)} {item_text}**"

        def describe_cost_list(cost_list):
            if len(cost_list) == 1:
                cost_text = f"You now have {describe_cost(cost_list[0])} remaining."
            elif len(cost_list) == 2:
                cost_text = f"You now have {describe_cost(cost_list[0])} and {describe_cost(cost_list[1])} remaining."
            else:
                cost_text = "You now have "
                length = len(cost_list)
                for i in range(length):
                    cost_text += describe_cost(cost_list[i])
                    if i < length-1:
                        cost_text += ", " 
                    if i == length-2:
                        cost_text += "and "
                cost_text += " remaining."
            return cost_text

        text = None
        
        ################################################################
        
        if issubclass(item, store.Catalyst):
            result = await self.buy_confirmation_catalyst(
                ctx = ctx,
                user_account = user_account,
                item = item
            )
            
            if not result:
                # If it returns false silently return, since the function
                # will likely have already sent a message to the player.
                return
            
            # Set the amount of items being bought to 1.
            item_count = 1

        ################################################################
        
        if issubclass(item, store.Ephemeral_Upgrade):
            result = await self.buy_confirmation_ephemeral(
                ctx = ctx,
                user_account = user_account,
                item = item
            )
            
            if not result:
                # If it returns false silently return, since the function
                # will likely have already sent a message to the player.
                return
            
            # Set the amount of items being bought to 1.
            item_count = 1
        
        ################################################################
        
        if item_count == 1:

            # if it exists but can't be bought, we say so
            if item not in buyable_items:
                # removed item is None check, as item will never be None. see above.
                await ctx.reply("Sorry, but you've already purchased as many of that as you can.")
                return
            
            try:
                if item.find_max_purchasable_count(user_account) <= 0:
                    await ctx.reply("Sorry, but you've already purchased as many of that as you can.")
                    return
            except AttributeError:
                # If an AttributeError was thrown the shop item probably doesn't have find_max_purchasable_count and we can ignore it.
                pass


            # now we check if the user has enough dough
            if not item.is_affordable_for(user_account):
                await ctx.reply("Sorry, but you can't afford to buy that.")
                return

            # now we actually purchase the item
            #user_account.increment("total_dough", -item.cost(user_account))
            print(f"{ctx.author.display_name} bought {item.display_name} for {item.cost(user_account)} dough")

            #print(f"item is {item}, user account is {user_account}, tuple is {(item, user_account)}")
            text = item.do_purchase(user_account)
            #user_account.increment(item.name, 1)
            self.json_interface.set_account(ctx.author,user_account, guild = ctx.guild.id)

            all_cost_types = item.get_cost_types(user_account)

            

            if len(all_cost_types) == 1:
                cost_text = f"You now have {describe_cost(all_cost_types[0])} remaining."
            elif len(all_cost_types) == 2:
                cost_text = f"You now have {describe_cost(all_cost_types[0])} and {describe_cost(all_cost_types[1])} remaining."
            else:
                cost_text = "You now have "
                length = len(all_cost_types)
                for i in range(length):
                    cost_text += describe_cost(all_cost_types[i])
                    if i < length-1:
                        cost_text += ", " 
                    if i == length-2:
                        cost_text += "and "
                cost_text += " remaining."

            if item in store.prestige_store_items:
                #await ctx.reply(f"Congratulations! You've unlocked the **{item.display_name}**! {text}")
                if text is None:
                    text = f"Congratulations! You've unlocked the **{item.display_name}** upgrade! You are now at level {user_account.get(item.name)}."
                
                #text += f"\n\nYou now have **{user_account.get(values.ascension_token.text)} {values.ascension_token.text}** remaining."
            else:
                if text is None:
                    an = "an" if item.display_name.lower()[0] in "aeiou" else "a"
                    text = f"You have purchased {an} {item.display_name}! You now have {user_account.get(item.name)} of them."

                #text += f"\n\nYou now have **{user_account.get('total_dough')} dough** remaining."

        else: # item count above 1

            # why make a new reference to store.all_store_items? all_items is already set to that.
            buyable_items = self.get_buyable_items(user_account, all_items)

            # revised buying code

            
            # check if the current class has the purchase_upper method
            if 'find_max_purchasable_count' in dir(i):
                max_purchasable = i.find_max_purchasable_count(user_account)

                # what's cool about this is all the price checks are done WITHIN find_max_purchasable_count
                # so we don't even have to check. purchase_num *should* be a valid purchase amount.
                # if item_count is larger than the amount you can afford, max_purchasable should be lower.
                # if you don't want to buy as much as you can, item_count will be lower.
                purchase_num = min(item_count,max_purchasable)

                # purchase the item! do_purchase modified to allow for item counts.
                # only items with the purchase_upper method should have the modified code.
                text = item.do_purchase(user_account,amount = purchase_num)

                purchased_count = purchase_num

            else:
                # old code, for use with items that don't have find_max_purchasable_count
                purchased_count = 0
                for i in range(item_count):

                    # buyable_items = self.get_buyable_items(user_account, all_items)
                    
                    # if item not in buyable_items:
                    #     break # if we've bought as many as we can legally

                    if not item.can_be_purchased(user_account):
                        break # if we've bought as many as we can legally

                    if not item.is_affordable_for(user_account):
                        break # if we've spent all our dough

                    text = item.do_purchase(user_account)
                    #user_account.increment(item.name, 1)

                    purchased_count += 1


            self.json_interface.set_account(ctx.author,user_account, guild = ctx.guild.id)

            print(f"{ctx.author.display_name} bought {purchased_count} {item.display_name}")
            if item in store.prestige_store_items:
                if text is None:
                    text = f"You have purchased {purchased_count} {item.display_name} upgrades! You are now at level {user_account.get(item.name)}."
                # text += f"\n\nYou now have **{user_account.get(values.ascension_token.text)} {values.ascension_token.text}** remaining."
            else: #normal item
                if text is None:
                    text = f"You have purchased {utility.write_count(purchased_count, item.display_name)}."# \n\nYou now have **{user_account.get('total_dough')} dough** remaining."

            # this will only describe the cost for the most recent level of the item purchased, but it's better than nothing.
            all_cost_types = item.get_cost_types(user_account)
            cost_text = describe_cost_list(all_cost_types)

            # text += "\n\n" + cost_text

        ending_buyable = self.get_buyable_items(user_account, store.all_store_items)
        
        # If the item is set to not show what is now available, this variable will be False.
        if item.show_available_when_bought:
            text += self.describe_added_shop_items(
                before = buyable_items,
                after = ending_buyable
            )
            
        text += "\n\n" + cost_text

        await ctx.reply(text)

        # complete chessatron on this command
        if ctx.author.id in self.currently_interacting:
            return
        self.currently_interacting.append(ctx.author.id)
        await self.do_chessboard_completion(ctx)
        await self.anarchy_chessatron_completion(ctx)
        self.remove_from_interacting(ctx.author.id)

        return


    # this function finds all the items the user is allowed to purchase
    def get_buyable_items(
            self: typing.Self,
            user_account: account.Bread_Account,
            item_list: list[store.Store_Item]
        ) -> list[store.Store_Item]:
        """Returns a list of every item in item_list that passes the can_be_purchased store item method."""
        # user_account = self.json_interface.get_account(ctx.author)
        output = []
        #for item in store.all_store_items:
        for item in item_list:
            # level = user_account.get(item.name)
            if item.can_be_purchased(user_account):
                output.append(item)
        return output

    

    ########################################################################################################################
    #####      BREAD GIFT

    bread_gift_text = """
You can gift both dough and items through this command.

For instance, "$bread gift Melodie 5" would gift 5 dough to Melodie.
"$bread gift Melodie 5 dough" also works.

Likewise, "$bread gift Melodie :croissant:" would gift a :croissant:,
and "$bread gift Melodie 5 :croissant:" would gift 5 of them.

Categories of items, such as special_bread or chess_pieces, can be gifted as a group. 
For instance, "$bread gift Melodie 5 special_bread" would gift 5 of each special bread to Melodie.

Instead of using a number, 'all', 'half' or 'quarter' can be used to gift that amount of the items.
For example, "$bread gift Melodie all chess_pieces" would gift all your chess pieces to Melodie.
"""

    @bread.command(
        brief="Gives bread away.",
        help="Usage: $bread gift [person] [amount] [item]\n"+bread_gift_text,
        aliases=["pay"]
    )
    async def gift(self, ctx, target: typing.Optional[discord.Member] = commands.parameter(description = "The person to gift to."), 
                    arg1: typing.Optional[typing.Union[parse_int, str]] = commands.parameter(description = "The amount you want to gift.", displayed_name = "amount"), 
                    arg2: typing.Optional[typing.Union[parse_int, str]] = commands.parameter(description = "The item you're gifting.", displayed_name = "item")):

        if ctx.author.id in self.currently_interacting:
            return
        self.currently_interacting.append(ctx.author.id)
        # await ctx.reply("This function isn't ready yet.")

        if target is None: #then it's empty and we'll tell them how to use it.
            await ctx.reply(self.bread_gift_text)
            self.remove_from_interacting(ctx.author.id)
            return

        sender_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
        receiver_account = self.json_interface.get_account(target, guild = ctx.guild.id)

        #file = self.json_interface.get_file_for_user(ctx.author)
        if "allowed" in sender_account.values.keys():
            if sender_account.values["allowed"] == False:
                await ctx.reply("Sorry, you are not allowed to gift bread.")
                self.remove_from_interacting(ctx.author.id)
                return
                
        bot_list = [ # These can always be gifted to.
            960869046323134514, # Machine-Mind
            973811353036927047, # Latent-Dreamer
            966474721619238972, # Tigran-W-Petrosian
            1029793702136254584, # Bingo-Bot
            466378653216014359, # PluralKit
        ]

        if receiver_account.get_prestige_level() > sender_account.get_prestige_level():
            if receiver_account.get("id") not in bot_list: # can always gift to bots
                await ctx.reply("Sorry, you can't gift to someone who has a higher ascension level than you.")
                self.remove_from_interacting(ctx.author.id)
                return
            
        if receiver_account.get("gifts_disabled") == True:
            await ctx.reply("Sorry, you can't gift to that person.")
            self.remove_from_interacting(ctx.author.id)
            return
        
        if sender_account.get("gifts_disabled") == True:
            await ctx.reply("Sorry, you can't gift right now. Please reenable gifting with \"$bread disable_gifts off\".")
            self.remove_from_interacting(ctx.author.id)
            return
        
        # Space gifting checks.
        if (sender_account.get_space_level() != 0 or receiver_account.get_space_level() != 0) and \
            (sender_account.get_prestige_level() == receiver_account.get_prestige_level()): # Space related checks should only run if the two accounts are on the same ascension.
            if sender_account.get_galaxy_location(self.json_interface, correct_center=True) != receiver_account.get_galaxy_location(self.json_interface, correct_center=True):
                send_check = space.gifting_check_user(
                    json_interface = self.json_interface,
                    user = sender_account
                )
                if not send_check:
                    await ctx.reply("You aren't able to access the Trade Hub network from where you are.")
                    self.remove_from_interacting(ctx.author.id)
                    return
                
                receiver_check = space.gifting_check_user(
                    json_interface = self.json_interface,
                    user = receiver_account
                )
                if not receiver_check:
                    await ctx.reply("You have access to the Trade Hub network, but you can't seem to reach that person.")
                    self.remove_from_interacting(ctx.author.id)
                    return
        
        if arg1 is None: # If arg1 is None, then arg2 is None as well.
            await ctx.reply("Needs an amount and what to gift.")
            self.remove_from_interacting(ctx.author.id)
            return
        
        do_fraction = False
        amount = 0
        do_category_gift = False


        if (type(arg1) is int and arg2 is None):
            emoji = "dough"
            amount = arg1
        elif arg2 is None:
            amount = 1
            emoji = arg1
        elif is_int(arg1):
            amount = int(arg1)
            emoji = arg2
        elif is_int(arg2):
            amount = int(arg2)
            emoji = arg1
            amount = 1
        elif is_fraction(arg1):
            do_fraction = True
            amount = 1
            fraction_numerator, fraction_denominator = parse_fraction(arg1)
            emoji = arg2
        
        
        elif str(arg1).lower() in ["all", "half", "third", "quarter"] or \
            str(arg2).lower() in ["all", "half", "third", "quarter"]:
            do_fraction = True
            amount = 1

            if str(arg1).lower() in ["all", "half", "third", "quarter"]:
                parse = str(arg1).lower()
                emoji = arg2
            else:
                parse = str(arg2).lower()
                emoji = arg1

            if parse == "all":
                fraction_numerator = 1
                fraction_denominator = 1
            elif parse == "half":
                fraction_numerator = 1
                fraction_denominator = 2
            elif parse == "quarter":
                fraction_numerator = 1
                fraction_denominator = 4
            else:
                fraction_numerator = 1
                fraction_denominator = 3
        else:
            await ctx.reply("Needs an amount and what to gift.")
            self.remove_from_interacting(ctx.author.id)
            return
        
        if do_fraction:
            if fraction_numerator > fraction_denominator:
                await ctx.reply("You can't gift more than what you have.")
                self.remove_from_interacting(ctx.author.id)
                return
            elif fraction_numerator == 0:
                await ctx.reply("That's not much of a gift.")
                self.remove_from_interacting(ctx.author.id)
                return

        def gift(
                sender_member: discord.Member,
                receiver_member: discord.Member,
                item: values.Emote,
                amount: int
            ):
            sender = self.json_interface.get_account(sender_member, sender_member.guild)
            receiver = self.json_interface.get_account(receiver_member, receiver_member.guild)

            sender.increment(item, -amount)
            receiver.increment(item, amount)
            
            # Save the accounts after gifting to ensure nothing is overwritten.
            self.json_interface.set_account(sender_member, sender, guild = ctx.guild.id)
            self.json_interface.set_account(target, receiver, guild = ctx.guild.id)

        # Gifting entire chess sets.
        if emoji == "chess_set":
            limiting_values = []

            for piece in values.all_chess_pieces:
                limiting_values.append(sender_account.get(piece.text) // values.all_chess_pieces_biased.count(piece))
            
            maximum_possible = min(limiting_values)

            if maximum_possible == 0:
                await ctx.reply("Sorry, you don't have any chess sets to gift.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            item_amount = min(maximum_possible, amount)

            if do_fraction:
                item_amount = maximum_possible * fraction_numerator // fraction_denominator
            
            # Now, recursively call this function for each item.
            for item in values.all_chess_pieces:
                gift_amount = item_amount * values.all_chess_pieces_biased.count(item)
                
                gift(
                    sender_member = ctx.author,
                    receiver_member = target,
                    item = item.text,
                    amount =gift_amount
                )
                await ctx.send(f"{utility.smart_number(gift_amount)} {item.text} has been gifted to {target.mention}.")
                await asyncio.sleep(1)
                
            await ctx.reply(f"Gifted {utility.write_count(item_amount, 'chess set')} to {receiver_account.get_display_name()}.")
            self.remove_from_interacting(ctx.author.id)
            return
        elif emoji in {"anarchy_piece_set", "anarchy_set"}:
            limiting_values = []

            for piece in values.all_anarchy_pieces:
                limiting_values.append(sender_account.get(piece.text) // values.all_anarchy_pieces_biased.count(piece))
            
            maximum_possible = min(limiting_values)

            if maximum_possible == 0:
                await ctx.reply("Sorry, you don't have any anarchy piece sets to gift.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            item_amount = min(maximum_possible, amount)

            if do_fraction:
                item_amount = maximum_possible * fraction_numerator // fraction_denominator
            
            # Now, recursively call this function for each item.
            for item in values.all_anarchy_pieces:
                gift_amount = item_amount * values.all_anarchy_pieces_biased.count(item)
                
                gift(
                    sender_member = ctx.author,
                    receiver_member = target,
                    item = item.text,
                    amount =gift_amount
                )
                await ctx.send(f"{utility.smart_number(gift_amount)} {item.text} has been gifted to {target.mention}.")
                await asyncio.sleep(1)
                
            await ctx.reply(f"Gifted {utility.write_count(item_amount, 'anarchy piece set')} to {receiver_account.get_display_name()}.")
            self.remove_from_interacting(ctx.author.id)
            return

        if sender_account.has_category(emoji):
            do_category_gift = True
            print(f"category gift of {emoji} detected")

        if do_category_gift is True:
            gifted_count = 0
            
            # we recursively call gift for each item in the category
            # and then return
            for item in sender_account.get_category(emoji):
                if do_fraction:
                    item_amount = sender_account.get(item.text) * fraction_numerator // fraction_denominator
                else:
                    item_amount = min(amount, sender_account.get(item.text))
                
                if item_amount > 0:
                    gifted_count += item_amount
                    gift(ctx.author, target, item.text, item_amount)

                    await ctx.send(f"{utility.smart_number(item_amount)} {item.text} has been gifted to {target.mention}.")
                    await asyncio.sleep(1)
                
            if gifted_count > 0:
                await ctx.reply(f"Gifted {utility.smart_number(gifted_count)} {emoji} to {receiver_account.get_display_name()}.")
            else:
                await ctx.reply(f"Sorry, you don't have any {emoji} to gift.")
            
            self.remove_from_interacting(ctx.author.id)
            return        

        emote = None

        if (emoji.lower() == "dough"):
            item = "total_dough"
            pass
        elif do_category_gift is True:
            pass # this block has no use if we're gifting a category
        else:
            # print(f"checking for gift with text {emoji}")
            emote = values.get_emote(emoji)
            if (emote is None) or (emote.can_be_gifted() == False):
                # print("failed to find emote")
                await ctx.reply("Sorry, that's not a giftable item.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            item = emote.text
        
        if do_fraction is True:
            # if we're gifting a category, go through every item in it and get the highest overall amount for "all"
            if do_category_gift is True:
                base_amount = 0
                for item in sender_account.get_category(emoji):
                    base_amount = max(base_amount, sender_account.get(item.text))
            # otherwise we're gifting a single item, so get the amount of that item
            else:
                base_amount = sender_account.get(item)

            amount = base_amount * fraction_numerator // fraction_denominator

        if ctx.author.id == target.id:
            await ctx.reply("You can't gift bread to yourself, silly.")
            print(f"rejecting self gift request from {target.display_name} for amount {amount}.")
            self.remove_from_interacting(ctx.author.id)
            
            return

        if (amount < 0):
            print(f"Rejecting steal request from {ctx.author.display_name}")
            await ctx.reply("Trying to steal bread? Mum won't be very happy about that.")
            await ctx.invoke(self.bot.get_command('brick'), member=ctx.author)
            self.remove_from_interacting(ctx.author.id)
            return
        
        if (amount == 0):
            print(f"Rejecting 0 bread request from {ctx.author.display_name}")
            await ctx.reply("That's not much of a gift.")
            self.remove_from_interacting(ctx.author.id)
            return


        # enforce maxumum gift amount to players of lower prestige level
        if receiver_account.get_prestige_level() < sender_account.get_prestige_level() and \
            item == "total_dough" and \
            receiver_account.get("id") not in bot_list: # can always gift to bots
            already_gifted = receiver_account.get("daily_gifts")
            max_gift = receiver_account.get_maximum_daily_gifts()
            leftover = max_gift - already_gifted
            if leftover <= 0:
                await ctx.reply("Sorry, they've already received as much dough as they can today.")
                self.remove_from_interacting(ctx.author.id)
                return
            if amount > leftover:
                await ctx.reply(f"Sorry, they can only recieve {leftover} more dough today. I will gift them that much.")
                amount = leftover
            if sender_account.has(item, amount):
                receiver_account.increment("daily_gifts", amount)
                self.json_interface.set_account(target, receiver_account, guild = ctx.guild.id)
            else:
                await ctx.reply("Except you don't have that much dough to give. Too bad.")
                self.remove_from_interacting(ctx.author.id)
                return

        # no gifting stonks to people of lower prestige level
        if receiver_account.get_prestige_level() < sender_account.get_prestige_level() and \
            emote is not None and \
            receiver_account.get("id") not in bot_list: # can always gift to bots
            if emote.text in all_stonks:
                await ctx.reply("Sorry, you can't gift stonks to people of lower prestige level.")
                self.remove_from_interacting(ctx.author.id)
                return

        # sender_account = self.json_interface.get_account(ctx.author)
        # receiver_account = self.json_interface.get_account(target)
        #if emote[]
        if emote is None:
            if sender_account.has(item, amount):
                gift(ctx.author, target, "total_dough", amount)
                
                print(f"{amount} dough has been gifted to {target.display_name} by {ctx.author.display_name}.")
                await ctx.send(f"{utility.smart_number(amount)} dough has been gifted to {target.mention}.")
            else:
                await ctx.reply("You don't have enough dough to gift that much.")
        else:
            if sender_account.has(item, amount):
                gift(ctx.author, target, item, amount)
                
                print(f"{amount} {item} has been gifted to {target.display_name} by {ctx.author.display_name}.")
                await ctx.send(f"{utility.smart_number(amount)} {item} has been gifted to {target.mention}.")
            else:
                await ctx.reply("You don't have enough of that to gift.")

        self.remove_from_interacting(ctx.author.id)
            #  we will not gift attributes after all, those will be trophies for the roller
            # for atrribute in emote.attributes:
            #     if sender_account.has(atrribute, amount):
            #         sender_account.increment(atrribute, -amount)
            #         receiver_account.increment(atrribute, amount)
        
        # self.json_interface.set_account(ctx.author, sender_account, guild = ctx.guild.id)
        # self.json_interface.set_account(target, receiver_account, guild = ctx.guild.id)

        # elif type(arg1) is None or type(arg2) is None:
        #     await ctx.reply("Needs an amount and what to gift.")
        #     return

    @bread.command(
        brief="Disables being gifted items.",
        aliases=["disable_gift, disablegifts, disablegift"]
    )
    async def disable_gifts(self, ctx,
            toggle: typing.Optional[str] = commands.parameter(description = "Whether to disable gifts. 'on' or 'off'.")
            ):
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
        state = user_account.get("gifts_disabled")

        if toggle == 'on':
            user_account.set("gifts_disabled", True)
            await ctx.reply("Other people can no longer gift you items.")
        elif toggle == 'off':
            user_account.set("gifts_disabled", False)
            await ctx.reply("You can now be gifted items again.")
        else:
            if state == False:
                user_account.set("gifts_disabled", True)
                await ctx.reply("Other people can no longer gift you items.")
            else:
                user_account.set("gifts_disabled", False)
                await ctx.reply("You can now be gifted items again.")
        
        self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)

        
        

    ########################################################################################################################
    #####      BREAD GAMBLE

    bread_gamble_info=\
"""In order to gamble, wager an amount.
The minimum wager is 4 and the maximum is 50.
You can gamble up to 20 times a day.
The results are worth the following:
horsey - Nothing.
fruit - 25% of your wager.
bread - 50% of your wager.
special bread - 200% of your wager.
chess piece - 400% of your wager.
anarchy - 1000% of your wager.
"""

    #gamble_list = []

    @bread.command(
        brief= "Risk / Reward.",
        help=bread_gamble_info,
        aliases = ["gramble"]
    )
    async def gamble(self, ctx,
            amount: typing.Optional[str] = commands.parameter(description = "The amount of dough to lay on the table.")
            ):
        if amount == "all":
            user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
            
            amount = min(
                user_account.get_dough(),
                user_account.get_maximum_gamble_wager()
            )
        else:
            try:
                amount = parse_int(amount)
            except ValueError:
                amount = None

        if amount is None:
            await ctx.send(self.bread_gamble_info)
            return

        #if ctx.channel.name not in earnable_channels:
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Sorry, but you can only do that in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return

        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
        
        

        minimum_wager = 4

        maximum_wager = user_account.get_maximum_gamble_wager()

        if amount < minimum_wager or user_account.get("total_dough") < minimum_wager:
            await ctx.reply(f"The minimum wager is {minimum_wager}.")
            return

        max_gambles = user_account.get("max_gambles")
        if user_account.has("daily_gambles", max_gambles):
            await ctx.reply(f"Sorry, you can only gamble {max_gambles} times today, unless you'd like to buy more passes at the shop.")
            return
        
        # Checks list of people currently gambling to prevent spam.
        # if they're already on the list
        if ctx.author.id in self.currently_interacting:
            print(f"rejecting duplicate request from {ctx.author.display_name}")
            return
        self.currently_interacting.append(ctx.author.id)

        # if user_account.has("total_dough", amount):
        #     pass
        # else:
        #     # await ctx.reply("You don't have that much dough.")
        #     # return
        #     amount = user_account.get("total_dough")
        #     await ctx.reply(f"You don't have that much dough. I'll enter in {amount} for you.")
        reply = ""
        if amount > maximum_wager:
            # set to maximum wager and notify
            amount = maximum_wager
            reply = f"The maximum wager is {utility.smart_number(maximum_wager)}. "
        if amount > user_account.get("total_dough"):
            # set to maximum dough and notify
            amount = user_account.get("total_dough")
            reply += f"You don't have that much dough. I'll enter in {utility.smart_number(amount)} for you."
        elif reply != "":
            reply += "I'll enter that in for you."

        print(f"{ctx.author.display_name} gambled {amount} dough")


        # if amount > maximum_wager and user_account.has("total_dough", maximum_wager):
        #     await ctx.reply(f"The maximum wager is {utility.smart_number(maximum_wager)}. I'll enter that in for you.")
        #     await asyncio.sleep(1)
        #     amount = maximum_wager
        # elif amount > maximum_wager and not user_account.has("total_dough", maximum_wager):
        #     amount = min(maximum_wager, user_account.get("total_dough"))
        #     await ctx.reply(f"You don't have that much dough. I'll enter in {utility.smart_number(amount)} for you.")
        #     await asyncio.sleep(1)
        # elif not user_account.has("total_dough", amount):
        #     await ctx.reply("You don't have that much dough. I'll enter in the maximum amount for you.")
        #     await asyncio.sleep(1)
        #     amount = user_account.get("total_dough")
        
        before_buyable = self.get_buyable_items(user_account, store.all_store_items)

        user_account.increment("daily_gambles", 1)
        user_account.increment("lifetime_gambles", 1)
        
        self.json_interface.set_account(ctx.author, user_account, ctx.guild.id)

        if reply != "":
            await ctx.reply(reply)
            await asyncio.sleep(1)
            
        game = gamble.BaseGame(
            wager = amount,
            json_interface = self.json_interface,
            ctx = ctx
        )
        
        await game.setup()
        
        await asyncio.sleep(2)
        
        while game.in_progress:
            await game.run_tick()
            
            await asyncio.sleep(1.5)

        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
        after_buyable = self.get_buyable_items(user_account, store.all_store_items)
        
        await game.finish(self.describe_added_shop_items(before_buyable, after_buyable))

        self.remove_from_interacting(ctx.author.id)


    def show_grid(
            self: typing.Self,
            grid: list[list[str]]
        ) -> str:
        """Renders a grid from a list of lists of strings."""
        output = ""
        for i in range(len(grid)):
            for k in range(len(grid[i])):
                if grid[i][k] is None:
                    output += ":black_medium_square: "
                else:
                    output += str(grid[i][k]) + " "
            output += "\n"
        return output

    ########################################################################################################################
    #####      BREAD STONKS

    @bread.group(
        name="stonks", 
        aliases=["stonk", "stocks", "stock", "yeast"],
        usage="stonks [buy/sell] [amount] [symbol]",
        brief="See the stonk market.",
    )
    async def stonks(self, ctx):
        if ctx.invoked_subcommand is not None:
            return
            #await ctx.send_help(ctx.command)

        output = "Welcome to the stonk market!\nCurrent values are as follows:\n\n"
        stonks_file = self.json_interface.get_custom_file("stonks", guild = ctx.guild.id)

        # #set default values
        # save = False
        # if values.pretzel.text not in stonks_file.keys():
        #     stonks_file[values.pretzel.text] = 100
        #     save = True
        # if values.cookie.text not in stonks_file.keys():
        #     stonks_file[values.cookie.text] = 25
        #     save = True
        # if values.fortune_cookie.text not in stonks_file.keys():
        #     stonks_file[values.fortune_cookie.text] = 500
        #     save = True
        # if save == True:
        #     self.json_interface.set_custom_file("stonks", stonks_file)

        for stonk in main_stonks:
            if stonk in stonks_file.keys():
                value = round(stonks_file[stonk])
                output += f"{stonk} - {utility.smart_number(value)} dough\n"

        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
        output += f"\nYou have **{utility.smart_number(user_account.get('total_dough'))} dough** to spend.\n"
        output += '\nUse "$bread invest <amount> <stonk>" to buy into a stonk.\nUse "$bread divest <amount> <stonk>" to get out while you\'re still behind.\nUse "$bread portfolio" to see your current stonk holdings.'
        await ctx.reply(output)


    previous_messages = list()

    async def stonks_announce(self: typing.Self) -> None:
        """Announces the new values of the stonks."""
        
        
        load_dotenv()
        IS_PRODUCTION = getenv('IS_PRODUCTION')
        print("IS_PRODUCTION is: "+IS_PRODUCTION)
        # if IS_PRODUCTION == "True":
        #     print("Stonk announce: This is a production server, continuing")
            
        # if IS_PRODUCTION == "False":
        #     print("Stonk announce: This is a development server, aborting")
        #     return
            
        # delete old messages
        for message in self.previous_messages:
            try:
                await message.delete()
            except:
                pass       
        self.previous_messages.clear()

        # define message
        for guild in self.json_interface.get_list_of_all_guilds():
            stonks_file = self.json_interface.get_custom_file("stonks", guild = guild)
            if stonks_file is None:
                continue
            guild_info = self.json_interface.get_guild_info(guild)
            announcement_channel_id = guild_info.get("announcement_channel", None)
            if announcement_channel_id is None:
                continue
            announcement_channel = self.bot.get_channel(int(announcement_channel_id))

            output = "Current stonk values are as follows:\n\n"
            for stonk in main_stonks:
                stonk_history_key = stonk+"_history"
                stonk_history = stonks_file[stonk_history_key] # will be a list

                output += f"{stonk}: "

                for entry_number in range(len(stonk_history)): # for each element of a list
                    historical_value = stonk_history[entry_number] # get the element
                    output += f"{round(historical_value)} -> " 
                    

                value = round(stonks_file[stonk])
                output += f"**{value}** dough"

                if stonk + "_split" in stonks_file:
                    if stonks_file[stonk + "_split"] is True:
                        output += " **(Split!)**"
                
                output += "\n"

            message = await announcement_channel.send(output)
            self.previous_messages.append(message)

        """
        # post messages
        if IS_PRODUCTION == "True":
            channel_ids =  announcement_channel_ids
        if IS_PRODUCTION == "False":
            channel_ids =  test_announcement_channel_ids
        for channel_id in channel_ids:
            channel = self.bot.get_channel(channel_id)
            if channel is not None:
                try:
                    message = await channel.send(output)
                    self.previous_messages.append(message)
                except:
                    pass
        """

    ########################################################################################################################
    #####      BREAD INVEST OLD
    """
    @bread.command(
        brief="Buy into a stonk.",
        help="You can either use the stonk name or the stonk emoji.\nUse as \"$bread invest <amount> <stonk>\". You can also invest a certain amount of dough by using \"$bread invest <amount> dough <stonk>\".",
    )
    async def invest_old(self, ctx, *, args):
        if ctx.channel.name not in earnable_channels:
            await ctx.reply("Thank you for your interest in stonks. They are available for you in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return

        amount = None
        emote = None
        dough_value = False

        args = args.split(" ")
        
        # see if we have 'dough' in the args
        for arg in args:
            if arg.lower() == "dough":
                dough_value = True

        # first get the amount from the args
        for arg in args:
            if is_digit(arg):
                amount = parse_int(arg)
                break
        if amount is None:
            for arg in args:
                if arg == "all":
                    amount = 1000000000
                    break
        if amount is None:
            for arg in args:
                if arg.startswith("-"):
                    await ctx.reply("You can't invest negative dough.")
                    return
        
        # then get the emote from the args
        for arg in args:
            test_emote = values.get_emote(arg)
            if test_emote is not None:
                print(f"found emote: {test_emote}")
                emote = test_emote
                break
        
        if emote is None or amount is None:
            await ctx.reply("Needs an amount and what to invest in.\nUse as \"$bread invest <amount> <stonk>\"")
            return

        if amount == 0:
            await ctx.reply("There's no point in investing 0 dough.")
            return
        
        # now we go through the stonks and see if we can find one that matches the emote
        stonks_file = self.json_interface.get_custom_file("stonks")
        user_account = self.json_interface.get_account(ctx.author)

        print (f"{ctx.author.name} is investing {amount} {emote} stonks for {amount} dough.")
        if emote.text not in stonks_file.keys():
            await ctx.reply("Sorry, I don't recognize that stonk.")
            return
        
        stonk_value = round(stonks_file[emote.text])

        #check if we're buying a certain amount of dough worth of a stonk, rather than a certain amount of stonks
        if dough_value is True:
            amount = math.floor(amount/stonk_value)

        # now we buy the stonks
        amount_purchased = 0
        for i in range(amount):
            if user_account.has("total_dough", stonk_value):
                user_account.increment("total_dough", -stonk_value)
                user_account.increment(emote.text, 1)
                user_account.increment("investment_profit", -stonk_value)
                amount_purchased += 1
            else: 
                break

        self.json_interface.set_account(ctx.author, user_account)
        
        await ctx.reply(f"You invested in {utility.smart_number(amount_purchased)} {emote.text} stonks for **{utility.smart_number(amount_purchased*stonk_value)} dough**.\n\nYou have **{utility.smart_number(user_account.get_dough())} dough** remaining.")
        print(f"{ctx.author.name} invested in {amount_purchased} {emote.name} stonks for {amount_purchased*stonk_value} dough.")
    """

    # BREAD INVEST NEW
    # credit to Aloe for her work on this
    @bread.command(
        brief="Buy into a stonk.",
        help="You can either use the stonk name or the stonk emoji.\nUse as \"$bread invest <amount> <stonk>\". You can also invest a certain amount of dough by using \"$bread invest <amount> dough <stonk>\".",
    )
    async def invest(self, ctx,
            *, args: typing.Optional[str] = commands.parameter(description = "See above for command syntax.")
            ):
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Thank you for your interest in stonks. They are available for you in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        if args is None:
            await ctx.reply("Needs an amount and what to invest in.\nUse as \"$bread invest <amount> <stonk>\"")
            return

        amount = None
        emote = None

        args = args.lower().split(' ')
        
        # check for negatives and valid inputs. priority: negative, digit, all.

        fraction_numerator = None
        fraction_denominator = None

        for arg in args:
            if arg.startswith('-'):
                await ctx.reply("You can't invest negative dough.")
                return
            if is_digit(arg):
                amount = parse_int(arg)
            if arg.count("/") == 1:
                arg_split = arg.split("/")
                if is_digit(arg_split[0]) and is_digit(arg_split[1]):
                    fraction_numerator = int(arg_split[0])
                    fraction_denominator = int(arg_split[1])

                    # So the amount needed message isn't sent, this will get overwitten later.
                    amount = 1000000
                    
        if fraction_denominator == 0:
            await ctx.reply("Please explain how that fraction works.")
            return

        if fraction_denominator is not None and fraction_denominator < 0:
            await ctx.reply("You can't invest negative dough.")
            return
        
        # This actually is required so it doen't send the needs an amount message, this will get overwitten later.
        if "all" in args or "half" in args or "quarter" in args or "third" in args:
            amount = 10000000
        
        # get the emote from the args

        # i know readability is important, so let me overview this
        # it packs all values of args run through the values.get_emote function into a map object. this map object is iterated over to find all non-None values.
              
        arg_emotes = [x for x in map(values.get_emote,args) if x]
  
        # if there are non-None values, run this code
        # if length is 0, the if doesn't run
  
        if len(arg_emotes):
            print(f"found emote: {arg_emotes[0]}")
            emote = arg_emotes[0]
        
        if emote is None or amount is None:
            await ctx.reply("Needs an amount and what to invest in.\nUse as \"$bread invest <amount> <stonk>\"")
            return

        if amount == 0:
            await ctx.reply("There's no point in investing 0 dough.")
            return
        
        # now we go through the stonks and see if we can find one that matches the emote
        stonks_file = self.json_interface.get_custom_file("stonks", guild = ctx.guild.id)
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        if emote.text not in main_stonks or emote.text not in stonks_file.keys():
            await ctx.reply("Sorry, I don't recognize that stonk.")
            return
        
        print(f"{ctx.author.name} is investing {amount} {emote} stonks for {amount} dough.")

        stonk_value = round(stonks_file[emote.text])

        #check if we're buying a certain amount of dough worth of a stonk, rather than a certain amount of stonks
        if 'dough' in args:
            # x //= n is the same as x = x // n, where // is floor division.
            amount //= stonk_value

        account_dough = user_account.get_dough()

        # this is here instead of at the top so
        # 1. the amount detection doesn't get annoyed at you for using all and 
        # 2. there's hopefully no weird behaviour if you use dough and all args
        if "all" in args:
            amount = account_dough // stonk_value
        
        if "half" in args:
            amount = account_dough // (stonk_value * 2)
        
        if "quarter" in args:
            amount = account_dough // (stonk_value * 4)

        if "third" in args:
            amount = account_dough // (stonk_value * 3)
        

        if fraction_numerator is not None:
            amount = (account_dough * fraction_numerator) // (fraction_denominator * stonk_value)

        # now we buy the stonks

        buy_amount = min(amount, account_dough // stonk_value)
        user_account.increment('total_dough',(-buy_amount * stonk_value))
        user_account.increment(emote.text, buy_amount)
        user_account.increment('investment_profit', (-buy_amount * stonk_value))

        self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)
        
        await ctx.reply(f"You invested in {utility.smart_number(buy_amount)} {emote.text} stonks for **{utility.smart_number(buy_amount*stonk_value)} dough**.\n\nYou have **{utility.smart_number(user_account.get_dough())} dough** remaining.")
        print(f"{ctx.author.name} invested in {buy_amount} {emote.name} stonks for {buy_amount*stonk_value} dough.")

    ########################################################################################################################
    #####      BREAD DIVEST OLD
    """
    # DIVEST OLD
    @bread.command(
        usage="divest <amount> <stonk>",
        brief="Get out of a stonk.",
        help="You can either use the stonk name or the stonk emoji.\nUse as \"$bread divest <amount> <stonk>\". You can also divest a certain amount of dough by using \"$bread divest <amount> dough <stonk>\".",
    )
    async def divest_old(self, ctx, *, args):
        if ctx.channel.name not in earnable_channels:
            await ctx.reply("Thank you for your interest in buying high and selling low. You can do so in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return

        stonks_file = self.json_interface.get_custom_file("stonks")
        user_account = self.json_interface.get_account(ctx.author)

        amount = None
        emote = None
        dough_value = False

        args = args.split(" ")

        #bread divest all: divests all stonks simultaneously
        if len(args) == 1:
            if args[0] == "all":
                amount_divested = 0
    
                for stonk in all_stonks:
                    while user_account.has(stonk, 1):
                        stonk_cost = round(stonks_file[stonk])
                        user_account.increment(stonk, -1)
                        user_account.increment("total_dough", stonk_cost)
                        user_account.increment("investment_profit", stonk_cost)
                        amount_divested += stonk_cost
                self.json_interface.set_account(ctx.author, user_account)
                await ctx.reply(f"You divested all of your stonks for **{utility.smart_number(amount_divested)} dough**.\n\nYou now have **{utility.smart_number(user_account.get_dough())} dough**.")
                return

        
        # see if we have 'dough' in the args
        for arg in args:
            if arg.lower() == "dough":
                dough_value = True

        # first get the amount from the args
        for arg in args:
            if is_digit(arg):
                amount = parse_int(arg)
                break
        if amount is None:
            for arg in args:
                if arg == "all":
                    amount = 1000000000
                    break
        if amount is None:
            for arg in args:
                if arg.startswith("-"):
                    await ctx.reply("You can't divest negative dough.")
                    return
        
        # then get the emote from the args
        for arg in args:
            test_emote = values.get_emote(arg)
            if test_emote is not None:
                print(f"found emote: {test_emote}")
                emote = test_emote
                break
        
        if emote is None or amount is None:
            await ctx.reply("Needs an amount and what to divest in.\nUse as \"$bread divest <amount> <stonk>\"")
            return

        if amount == 0:
            await ctx.reply("It would be silly to divest 0 stonks.")
            return

        

        # make sure the stonk is in the stonks file
        if emote.text not in stonks_file.keys():
            await ctx.reply("Sorry, I don't recognize that stonk.")
            return

        stonk_value = round(stonks_file[emote.text])
        #check if we're selling a certain amount of dough worth of a stonk, rather than a certain amount of stonks
        if dough_value is True:
            amount = math.ceil(amount/stonk_value)

        # now we sell the stonks
        amount_sold = 0
        for i in range(amount):
            if user_account.has(emote.text):
                user_account.increment("total_dough", stonk_value)
                user_account.increment(emote.text, -1)
                user_account.increment("investment_profit", stonk_value)
                amount_sold += 1
            else: 
                break
            
        self.json_interface.set_account(ctx.author, user_account)

        await ctx.reply(f"You sold {utility.smart_number(amount_sold)} {emote.text} stonks for **{utility.smart_number(amount_sold*stonk_value)} dough**. You now have **{utility.smart_number(user_account.get_dough())} dough** and {utility.smart_number(user_account.get(emote.text))} {emote.text}.")
        print (f"{ctx.author.name} divested in {amount_sold} {emote.text} stonks for {amount_sold*stonk_value} dough.")
    """

    ########################################################################################################################
    #####      BREAD DIVEST

    # DIVEST NEW
    # credit to Aloe for her work on this
    @bread.command(
        usage="divest <amount> <stonk>",
        brief="Get out of a stonk.",
        help="You can either use the stonk name or the stonk emoji.\nUse as \"$bread divest <amount> <stonk>\". You can also divest a certain amount of dough by using \"$bread divest <amount> dough <stonk>\".",
    )
    async def divest(self, ctx,
            *, args: typing.Optional[str] = commands.parameter(description = "See above for command syntax.")
            ):
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Thank you for your interest in buying high and selling low. You can do so in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        print(args)
        if args is None:
            await ctx.reply("Needs an amount and what to divest from.\nUse as \"$bread divest <amount> <stonk>\"")
            return

        stonks_file = self.json_interface.get_custom_file("stonks", guild = ctx.guild.id)
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        amount = None
        emote = None
        dough_value = False

        args = args.lower().split(' ')

        # divest all: divests all stonks simultaneously
        if len(args) == 1:
            if args[0] == "all":
                
                amount_divested = 0
                for stonk in main_stonks:
                    if stonk not in stonks_file.keys():
                        continue
                    stonk_cost = round(stonks_file[stonk])

                    profit = stonk_cost*user_account.get(stonk)
                    amount_divested += profit
                    user_account.increment('total_dough', profit)
                    user_account.increment("investment_profit", profit)
                    user_account.set(stonk, 0) # sell all the stonk by definition

                    self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)
                await ctx.reply(f"You divested all of your stonks for **{utility.smart_number(amount_divested)} dough**.\n\nYou now have **{utility.smart_number(user_account.get_dough())} dough**.")
                return
        
        # check for negatives and valid inputs. priority: negative, digit, all.

        fraction_numerator = None
        fraction_denominator = None

        for arg in args:
            if arg.startswith('-'):
                await ctx.reply("You can't divest negative dough.")
                return
            if is_digit(arg):
                amount = parse_int(arg)
            if arg == 'all':
                amount = -1
            if arg == "half":
                fraction_numerator = 1
                fraction_denominator = 2
                amount = -2
            if arg == "quarter":
                fraction_numerator = 1
                fraction_denominator = 4
                amount = -2
            if arg == "third":
                fraction_numerator = 1
                fraction_denominator = 3
                amount = -2
            if arg == 'dough':
                print("dough arg found in divest")
                dough_value = True
            if arg.count("/") == 1:
                arg_split = arg.split("/")
                if is_digit(arg_split[0]) and is_digit(arg_split[1]):
                    fraction_numerator = int(arg_split[0])
                    fraction_denominator = int(arg_split[1])

                    amount = -2
                    
        if fraction_denominator == 0:
            await ctx.reply("Please explain how that fraction works.")
            return

        if fraction_denominator is not None and fraction_denominator < 0:
            await ctx.reply("You can't invest negative dough.")
            return
        
        # then get the emote from the args
        for arg in args:
            test_emote = values.get_emote(arg)
            if test_emote is not None:
                # print(f"found emote: {test_emote}")
                emote = test_emote
                break
        
        if emote is None or amount is None:
            await ctx.reply("Needs an amount and what to divest from.\nUse as \"$bread divest <amount> <stonk>\"")
            return

        if amount == 0:
            await ctx.reply("It would be silly to divest 0 stonks.")
            return

        

        # make sure the stonk is in the stonks file
        if emote.text not in main_stonks:
            await ctx.reply("Sorry, I don't recognize that stonk.")
            return

        stonk_value = round(stonks_file[emote.text])
        #check if we're selling a certain amount of dough worth of a stonk, rather than a certain amount of stonks
        if dough_value is True and not amount == -1:
            amount = math.ceil(amount/stonk_value)

        # now we adjust the amount to make sure we don't sell more than we have
        if amount > user_account.get(emote.text) or amount == -1:
            amount = user_account.get(emote.text)
        
        if fraction_numerator is not None:
            amount = (user_account.get(emote.text) * fraction_numerator) // fraction_denominator
        
        # sell the stonks
        amount = min(amount, user_account.get(emote.text))
        user_account.increment('total_dough', stonk_value*amount)
        user_account.increment(emote.text, -amount)
        user_account.increment('investment_profit', stonk_value*amount)
            
        self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)

        await ctx.reply(f"You sold {utility.smart_number(amount)} {emote.text} stonks for **{utility.smart_number(amount*stonk_value)} dough**. You now have **{utility.smart_number(user_account.get_dough())} dough** and {utility.smart_number(user_account.get(emote.text))} {emote.text}.")
        print (f"{ctx.author.name} divested in {amount} {emote.text} stonks for {amount*stonk_value} dough.")

    ########################################################################################################################
    #####      BREAD PORTFOLIO

    @bread.command(
        name="portfolio", 
        aliases = ["investments"],
        brief="See your investments.",
    )
    async def portfolio(self, ctx,
            user: typing.Optional[discord.Member] = commands.parameter(description = "Who you want to get the portfolio of.")
            ):
        print(f"{ctx.author.name} requested their portfolio.")

        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_BASIC:
            await ctx.reply(f"Thank you for your interest in your stonks portfolio. We have it available for you in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        if user is None:
            user = ctx.author

        user_account = self.json_interface.get_account(user, guild = ctx.guild.id)

        # investments = user_account.get_all_items_with_attribute("stonks")
        stonks_file = self.json_interface.get_custom_file("stonks", guild = ctx.guild.id)

        output = f"Investment portfolio for {user_account.get_display_name()}:\n\n"
        total_value = 0
        history_value = 0
        num_stonks_held = 0

        for stonk in main_stonks:
            if user_account.has(stonk):
                num_stonks_held += 1
                stonk_text = stonk #stonk.text
                stonk_count = user_account.get(stonk_text)
                stonk_value = round(stonks_file[stonk_text])
                #print(f"stonk: {stonk}")
                value = stonk_count * stonk_value
                total_value += value
                output += f"{stonk_text} -- {utility.write_count(stonk_count, 'stonk')}, worth **{utility.smart_number(value)} dough**\n"

                history_name = f"{stonk_text}_history"
                if history_name in stonks_file.keys() and len(stonks_file[history_name]) >= 3:
                    history_value += stonk_count * round(stonks_file[history_name][2])

        if num_stonks_held == 0:
            output += "Your portfolio seems to be empty.\n\n"
        else:
            output += f"\nYour portfolio is worth **{utility.smart_number(total_value)} dough**. In the last tick, your portfolio value changed by **{utility.smart_number(total_value-history_value)} dough**. "
        
        investment_profit = user_account.get("investment_profit")
        output +=  f"So far, you've made **{utility.smart_number(investment_profit+total_value)} dough** from investing."

        await ctx.reply(output)
        
        
    ########################################################################################################################
    #####      Stonk internal stuff

    
    def stonk_fluctuate_internal(self: typing.Self) -> None:
        """Fluctuates the stonk values for each guild in the JSON interface."""

        stonk_starting_values = {
            ":cookie:": 25,
            ":pretzel:": 100,
            ":fortune_cookie:": 500,
            ":pancakes:": 2_500,
            ":cake:": 21_000,
            ":pizza:": 168_000,
            ":pie:": 1_512_000,
            ":cupcake:": 15_120_000
        }

        all_guild_ids = self.json_interface.get_list_of_all_guilds()
        for guild_id in all_guild_ids:
            print(f"stonk fluctuate: checking guild {get_name_from_guild(guild_id)}")
            stonks_file = self.json_interface.get_custom_file("stonks", guild = guild_id)

            # initialize stonks if they're not already
            for stonk in all_stonks:
                if stonk not in stonks_file.keys():
                    print(f"stonk {stonk} not in stonks file, initializing")
                    stonks_file[stonk] = stonk_starting_values[stonk]
                if stonk + "_history" not in stonks_file.keys():
                    stonks_file[stonk + "_history"] = []
                        
            # it's in a try block so that it won't crash if running on a server without the stonks file
            try:
                stonks_file = stonks.stonk_fluctuate(stonks_file) # this will forever remain a secret
            except:
                print("stonk fluctuate failed")
            
            # stonk autosplit code
            for stonk in all_stonks:
                stonks_file[stonk + "_split"] = False # Reset the split marker to false, so stonks_announce() won't say the stonk got split when it didn't.
                # print (f"stonks file is {stonks_file}")
                if stonks_file[stonk] >= stonk_starting_values[stonk] * 2:
                    if stonks_file[stonk] >= stonk_starting_values[stonk] * 3: # If the stonk is above 3x the starting value then split it no matter the history.
                        self.stonk_split_internal(stonk, guild= guild_id)
                        stonks_file[stonk + "_split"] = True # Set the split marker to true so stonks_announce() will say it got split.
                        continue

                    if stonk + "_history" not in stonks_file:
                        continue # If the history doesn't exist, then just skip to the next stonk.

                    stonk_history = stonks_file[stonk + "_history"] + [stonks_file[stonk]]
                    rise_fall = []

                    for tick_id in range(len(stonk_history) - 1): # Subtract 1 so it doesn't check the current values and future values that do not exist.
                        rise_fall.append(stonk_history[tick_id] >= stonk_history[tick_id + 1]) # Append a bool for whether the stonk rose, fell, or stagnated. True is fall or stagnate, False is a rise.
                    
                    if rise_fall.count(True) >= 2: # If the stonk fell or stagnated 2 or more times in the history data read.
                        self.stonk_split_internal(stonk, guild = guild_id)
                        stonks_file[stonk + "_split"] = True # Set the split marker to true so stonks_announce() will say it got split.
            
            self.json_interface.set_custom_file("stonks", stonks_file, guild = guild_id)
        # auto split code here?
        # I put the auto splitting code before stonk_fluctuate so the data that is used to determine a split is visible to players before the split occurs.

        # dividend code here?

        
    

    def stonk_reset_internal(
            self: typing.Self,
            guild: typing.Union[discord.Guild, int, str]
        ) -> None:
        """Resets the stonks to their original values."""

        stonks_file = self.json_interface.get_custom_file("stonks", guild = guild)

        # Set default values

        # Main stonks:
        stonks_file[values.pretzel.text] = 100
        stonks_file[values.cookie.text] = 25
        stonks_file[values.fortune_cookie.text] = 500
        stonks_file[values.pancakes.text] = 2500
        
        # Shadow stonks:
        stonks_file[values.cake.text] = 21000
        stonks_file[values.pizza.text] = 168000
        stonks_file[values.pie.text] = 1512000
        stonks_file[values.cupcake.text] = 15120000

        self.json_interface.set_custom_file("stonks", stonks_file, guild=guild)

    def stonk_split_internal(
            self: typing.Self,
            stonk_text: str,
            guild: typing.Union[discord.Guild, int, str]
        ) -> None:
        """Splits a stonk in half, while compensating those who had invested."""

        guild_id = get_id_from_guild(guild)

        stonks_file = self.json_interface.get_custom_file("stonks", guild = guild_id)
        stonk_value = stonks_file[stonk_text]
        stonks_file[stonk_text] = stonk_value/2

        # for a while we would split all the history values as well so that the portfolio command would
        # show a more reasonable value, but this messes with the display of a stonk_split message.
        # history_file = stonks_file.get(stonk_text+"_history", [])

        # for i in range(len(history_file)):
        #     history_file[i] = history_file[i]/2

        # stonks_file[stonk_text+"_history"] = history_file
            

        self.json_interface.set_custom_file("stonks", stonks_file, guild = guild_id)

        #now we go through everyone's investments and split them
        # user_files = self.json_interface.data[guild_id]

        #wipe the accounts cache since we'll be direcly manipulating data. 
        # Would be better to avoid this in the future.
        # self.json_interface.accounts.clear()

        # for file_key in user_files.keys():
        #     if not is_digit(file_key): # skip all non-user files
        #         continue
        #     file = user_files[file_key]
        #     #print(f"Individual file is: \n{file}")
        #     if stonk_text in file.keys():
        #         file[stonk_text] = file[stonk_text] * 2

        all_accounts_in_guild = self.json_interface.get_all_user_accounts(guild_id)
        for account in all_accounts_in_guild:
            if account.has(stonk_text):
                account.set(stonk_text, account.get(stonk_text) * 2)
                self.json_interface.set_account(account.values["id"], account, guild = guild_id)

        print(f"{stonk_text} has been split into two stonks")


    def get_portfolio_value(
            self: typing.Self,
            user_id: int,
            guild: typing.Union[discord.Guild, int, str]
        ) -> int:
        """Returns the portfolio value of the given user id."""
        guild_id = get_id_from_guild(guild)
        stonks_file = self.json_interface.get_custom_file("stonks", guild_id)
        user_file = self.json_interface.get_account(user_id, guild_id)
        investments = user_file.get_all_items_with_attribute("stonks")
        total_value = 0
        for stonk in investments:
            stonk_text = stonk.text
            stonk_count = user_file.get(stonk_text)
            stonk_value = round(stonks_file[stonk_text])
            value = stonk_count * stonk_value
            total_value += value
        return total_value


    def get_portfolio_combined_value(
            self: typing.Self,
            user_id: int,
            guild: typing.Union[discord.Guild, int, str]
        ) -> int:
        """Takes the user's portfolio value and adds it to their investment_profit stat."""
        user_file = self.json_interface.get_account(user_id, guild)
        portfolio_value = self.get_portfolio_value(user_id, guild)
        return portfolio_value + user_file.get("investment_profit")

    

    ########################################################################################################################
    #####      BREAD ALCHEMY

    @bread.command(
        name="alchemy", 
        aliases = ["alchemize", "distill"],
        brief="Create a new item from base materials.",
        usage="<amount> <target item> <recipe number>",
        help="Creates more advanced materials from basic ones. Call the command and follow the instructions, keeping in mind what you would like to create."
    )
    #@commands.is_owner()
    async def alchemy(self, ctx,
            count: typing.Optional[parse_int] = commands.parameter(description = "The amount of the item you want to make."),
            target_item: typing.Optional[str] = commands.parameter(description = "The item to create."),
            recipe_num: typing.Optional[parse_int] = commands.parameter(description = "The recipe number to use."),
            confirm: typing.Optional[str] = commands.parameter(description = "Whether to confirm automatically.")
        ):
        
        if count is None:
            count = 1
        if count == 0:
            await ctx.reply("Alright, I have made zero of those for you...")
            return
        if count < 0:
            await ctx.reply("The laws of alchemy prevent me from utilizing negative energy.")
            return
        if count > 1000000000000000:
            await ctx.reply("That is an unreasonable number of items to alchemize. Please try again with a smaller number.")
            return

        # print(f"{ctx.author.name} requested to alchemize {count} {target_item}.")

        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Thank you for your interest in bread alchemy. Please find the alchemical circle is present in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return

        #check if they're already alchemizing
        if ctx.author.id in self.currently_interacting:
            return
        #otherwise we add them to the list
        self.currently_interacting.append(ctx.author.id)


        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        # transform it into a comprehensible string
        # target_item = values.get_emote(target_item)
        
        # create a reaction collector to listen for reactions
        def check(m: discord.Message):  # m = discord.Message.
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id 


        try: # this is to catch any errors on discord's end

            ########################################################################################################################
            #####      GET ITEM

            if (target_item is None):
                await ctx.reply("Welcome to the alchemy circle. Please say the item you would like to create.")
                try:
                    msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
                except asyncio.TimeoutError: 
                    # at this point, the check didn't become True, let's handle it.
                    await ctx.reply(f"My patience is limited. Come back when you know what you want.")
                    self.remove_from_interacting(ctx.author.id)
                    return
                target_item = msg.content #values.get_emote(msg.content)

            ########################################################################################################################
            #####      GET EMOTE

            # now we turn the target item into a useful emote
            target_emote = values.get_emote(target_item)

            if (target_emote is None):
                await ctx.reply(f"I do not recognize that item. Please start over.")
                self.remove_from_interacting(ctx.author.id)
                return

            print(f"{ctx.author.name} requested to alchemize {count} {target_emote.name}.")
            # print(f"Available recipes are: {alchemy.recipes}")

            if target_emote.name in alchemy.recipes.keys():
                recipe_list = alchemy.recipes[target_emote.name].copy()

                # Remove recipes that the user doesn't have the requirements for.
                # To do this, we iterate through a copy of the recipe list and check each requirement to make sure the user has that requirement.
                # If the user does not, we remove the item from the original recipe_list, because we're iterating through the copy the iteration is not messed up.

                for recipe in recipe_list.copy():
                    if "requirement" not in recipe:
                        continue # Recipe doesn't have any requirements.
                        
                    for requirement in recipe["requirement"]:
                        # Assume it's a callable and attempt to call it, but fall back on unpacking the requirement if it isn't a callable.
                        try:
                            if not requirement(user_account):
                                recipe_list.remove(recipe)
                                break
                        except TypeError: # If the requirement isn't a callable a TypeError will be raised.
                            require_key, require_amount = requirement
                            if user_account.get(require_key) < require_amount:
                                # User does not have a requirement.
                                recipe_list.remove(recipe)
                                break
                                
                if len(recipe_list) == 0:
                    # Either the recipe list was initially blank, in which there is some issue, or the user has not unlocked any recipes for the item yet.
                    await ctx.reply(f"I'm sorry, but your technology has not yet found a way to create {target_emote.text}.")
                    self.remove_from_interacting(ctx.author.id)
                    return
            else:
                await ctx.reply(f"There are no recipes to create {target_emote.text}. Perhaps research has not progressed far enough.")
                self.remove_from_interacting(ctx.author.id)
                return

            ########################################################################################################################
            #####      GET NUMBER

            if recipe_num is None:

                ingredients = list()

                recipes_description = f"There are {len(recipe_list)} recipes for {target_emote.text}.\n"
                for i in range(len(recipe_list)):
                    recipe = recipe_list[i]
                    recipes_description += f"**[ {i+1} ]**    {alchemy.describe_individual_recipe(recipe)}"

                    if "result" in recipe:
                        result_amount = recipe['result']

                        # Check if the result amount is a callable by trying to call it and catching the TypeError that occurs if it isn't.
                        try:
                            result_amount = result_amount(user_account)
                        except TypeError:
                            pass
                
                        # If it's a float and represents an integer just convert it to an integer.
                        # If it's already an integer it'll raise an AttributeError, which will be caught.
                        try:
                            if result_amount.is_integer():
                                result_amount = int(result_amount)
                        except AttributeError:
                            pass

                        recipes_description += f"   **({result_amount}x)**"

                    recipes_description += "\n"

                    # print (f"recipe is {recipe}")
                    
                    for pair in recipe["cost"]:
                        if pair[0] not in ingredients:
                            ingredients.append(pair[0])

                recipes_description += "\nOf the above ingredients, you have:\n"

                # show how much of each ingredient is posessed
                for ingredient in ingredients:
                    recipes_description += f"{ingredient.text}: {utility.smart_number(user_account.get(ingredient.text))}\n"
            
                recipes_description += "\nPlease reply with either the number of the recipe you would like to use, or \"cancel\"."
                await ctx.reply(recipes_description)
                
                try:
                    msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
                except asyncio.TimeoutError: 
                    # at this point, the check didn't become True, let's handle it.
                    await ctx.reply(f"My patience is limited. This offering is rejected.")
                    self.remove_from_interacting(ctx.author.id)
                    return

                if "cancel" in msg.content.lower():
                    await ctx.reply("You have cancelled this transaction.")
                    self.remove_from_interacting(ctx.author.id)
                    return

                try:
                    recipe_num = parse_int(msg.content)
                except ValueError:
                    await ctx.reply(f"I do not recognize that as a number. Please try again from the beginning.")
                    self.remove_from_interacting(ctx.author.id)
                    return
            
            if recipe_num > len(recipe_list) or recipe_num < 1:
                await ctx.reply(f"That is not a valid recipe number. Please start over.")
                self.remove_from_interacting(ctx.author.id)
                return

            recipe = recipe_list[recipe_num-1]

            ########################################################################################################################
            #####      GET CONFIRMATION

            item_multiplier = 1 # Amount of the output item to provide, by default it's 1 but something else can be specified via the recipe in alchemy.py.
            if "result" in recipe:
                item_multiplier = recipe["result"]

                # Check if the result amount is a callable by trying to call it and catching the TypeError that occurs if it isn't.
                try:
                    item_multiplier = item_multiplier(user_account)
                except TypeError:
                    pass
                
                # If it's a float and represents an integer just convert it to an integer.
                # If it's already an integer it'll raise an AttributeError, which will be caught.
                try:
                    if item_multiplier.is_integer():
                        item_multiplier = int(item_multiplier)
                except AttributeError:
                    pass

            already_confirmed = False
            if confirm is not None:
                if confirm.lower() in ["yes", "y", "confirm"]:
                    already_confirmed = True

            if already_confirmed is False:
                multiplier_text = ""
                if "result" in recipe:
                    multiplier_text = f"**({item_multiplier}x recipe)** "

                question_text = f"You have chosen to create {utility.smart_number(round(count * item_multiplier))} {target_emote.text} {multiplier_text}from the following recipe:\n{alchemy.describe_individual_recipe(recipe)}\n\n"
                question_text += f"You have the following ingredients:\n"
                for pair in recipe["cost"]:
                    question_text += f"{pair[0].text}: {utility.smart_number(user_account.get(pair[0].text))} of {round(pair[1] * count)}\n"
                        
                question_text += "\nWould you like to proceed? Yes or No."
                await ctx.reply(question_text)

                try:
                    msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
                except asyncio.TimeoutError:
                    await ctx.reply(f"My patience is limited. This offering is rejected.")
                    self.remove_from_interacting(ctx.author.id)
                    return
                
                content = msg.content.lower()
                
                if any([i in content for i in ["yes", "y", "confirm"]]):
                    pass
                elif any([i in content for i in ["no", "n", "deny"]]):
                    await ctx.reply("You have rejected this recipe.")
                    self.remove_from_interacting(ctx.author.id)
                    return
                else:
                    await ctx.reply("I do not recognize your response. You may come back when you are feeling more decisive.")
                    self.remove_from_interacting(ctx.author.id)
                    return

            ########################################################################################################################
            #####      CREATE ITEM

            user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

            # first we make sure the user has enough ingredients
            for pair in recipe["cost"]:
                cost = pair[1] * count
                posessions = user_account.get(pair[0].text)
                # print(f"{ctx.author.display_name} is attempting to alchemize {count} {target_emote.name}")
                # print(f"cost is {cost} and posessions is {posessions}")
                if posessions < cost:
                    await ctx.reply(f"You do not have enough {pair[0].text} to create {utility.smart_number(count)} {target_emote.text}. This offering is rejected.")
                    self.remove_from_interacting(ctx.author.id)
                    return
            
            ##### If the person is making fuel, ensure if it's fuel the person has enough fuel in their fuel tank.
            
            output_amount = item_multiplier
            
            value = 0

            override_dough = False
            if "provide_no_dough" in recipe and recipe["provide_no_dough"]:
                override_dough = True # Provide no dough from the recipe, even if the item calls for it. This is set in the recipe, instead of the item.

            # for i in range(count):
            # we remove the ingredients
            for pair in recipe["cost"]:
                user_account.increment(pair[0].text, -pair[1] * count)

            # then we add the item
            
            user_account.add_item_attributes(target_emote, output_amount * count)
            if target_emote.gives_alchemy_award() and not override_dough:
                value += user_account.add_dough_intelligent((target_emote.get_alchemy_value() + user_account.get_dough_boost_for_item(target_emote)) * item_multiplier * count)


            # finally, we save the account
            self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)

            output = f"Well done. You have created {utility.smart_number(count * output_amount)} {target_emote.text}. You now have {utility.smart_number(user_account.get(target_emote.text))} of them."
            if target_emote.gives_alchemy_award() and not override_dough:
                output += f"\nYou have also been awarded **{utility.smart_number(value)} dough** for your efforts."

            await ctx.reply(output)

            await self.do_chessboard_completion(ctx)
            await self.anarchy_chessatron_completion(ctx)

        except:
            print(traceback.format_exc())
            pass

        self.remove_from_interacting(ctx.author.id)
        
    ########################################################################################################################
    #####      BREAD DOUGH

    # get someone's amount of dough and display it
    @bread.command(
        aliases = ["liquid_dough"],
        brief = "Shows how much dough you have.",
    )
    async def dough(self, ctx,
            target: typing.Optional[discord.Member] = commands.parameter(description="The player to get the dough of.")
        ):
        if target is None:
            target = ctx.author

        user_account = self.json_interface.get_account(target, guild = ctx.guild.id)

        if target == ctx.author:
            name = "You have"
        else:
            name = user_account.get_display_name() + " has"
        
        await ctx.reply(f"{name} **{utility.smart_number(user_account.get_dough())} dough**.")








        
    ########################################################################################################################
    #####      BREAD SPACE

    @bread.group(
        brief = "Space travel in the Bread Game.",
    )
    async def space(self, ctx):
        # Ensure no subcommands have been run.
        if ctx.invoked_subcommand is not None:
            return
        
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Thank you for your interest in space travel! The nearest launch site is over in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return

        
        account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        if account.get_space_level() < 1:
            await ctx.reply("You do not yet have a rocket.\nYou can purchase one from the Space Shop, which is viewable via '$bread space shop'.")
            return
        
        # Player has a rocket!

        message = "Nice job getting a rocket!\n\nHere's a handy list of things you can do:\n"

        # Generate a list of the bread space subcommands and their help text.
        for cmd in self.space.commands:
            message += f"\t'$bread space {cmd.name}': {cmd.brief}\n"
        
        await ctx.reply(message)
        
        
        
    ########################################################################################################################
    #####      BREAD SPACE STATS

    @bread.command(
        name = "space_stats",
        brief = "Get your space stats.",
        description = "Shortcut to '$bread space stats'.",
        hidden = True
    )
    async def space_stats_shortcut(self, ctx,
            user: typing.Optional[discord.Member] = commands.parameter(description = "The user to get the stats of.")
        ):
        await self.space_stats(ctx, user)

    @space.command(
        name = "stats",
        brief = "See your space stats."
    )
    async def space_stats(self, ctx,
            user: typing.Optional[discord.Member] = commands.parameter(description = "The user to get the stats of.")
        ):
        # Ensure you can actually get your stats here.
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_BASIC:
            await ctx.send("Sorry, you can't do that here.")
            return
        
        if user is None:
            user = ctx.author
        
        user_account = self.json_interface.get_account(user, guild = ctx.guild.id)

        if user_account.get_space_level() < 1:
            if user == ctx.author:
                await ctx.reply("You do not yet have any space stats.")
            else:
                await ctx.reply(f"{user_account.get_display_name()} does not yet have any space stats.")
            return
        
        sn = utility.smart_number

        output = []

        # The items in the output list get joined with a new line in the middle, so only a single \n is required here.
        output.append(f"Space stats for: {user_account.get_display_name()}:\n")

        output.append(f"You have a tier {sn(user_account.get_space_level())} Bread Rocket.")
        output.append(f"Your location in the galaxy is currently {user_account.get_galaxy_location(self.json_interface)}.")

        daily_fuel_cap = user_account.get_daily_fuel_cap()
        project_credits_cap = user_account.get_projects_credits_cap()
        output.append(f"Out of your {sn(daily_fuel_cap)} {values.daily_fuel.text} you have {sn(user_account.get('daily_fuel'))} remaining.")
        output.append(f"From your {sn(project_credits_cap)} daily {values.project_credits.text} you have {sn(user_account.get('hub_credits'))} remaining.")

        output.append(f"With {utility.write_count(user_account.get(values.anarchy_omega_chessatron.text), 'Anarchy Omega Chessatron')} you get {sn(user_account.get_anarchy_chessatron_dough_amount(True))} for each new anarchy chessatron.")


        output.append("")

        if user_account.has(store.Upgraded_Autopilot.name):
            autopilot_level = user_account.get(store.Upgraded_Autopilot.name)

            messages = [
                "",
                "explore the galaxy",
                "adventure through nebulae",
                "travel through wormholes"
            ]

            message = ""
            for i in range(1, autopilot_level + 1):
                if i != 1 and i != autopilot_level:
                    message += ", "

                if i == autopilot_level and i != 1:
                    message += " and "

                message += messages[i]

            output.append(f"With a level {sn(autopilot_level)} autopilot you can {message}.")

        if user_account.has("fuel_tank"):
            level = user_account.get('fuel_tank')
            output.append(f"Your {values.daily_fuel.text} cap is increased by {sn(level * store.Fuel_Tank.multiplier)} with {utility.write_count(level, 'Fuel Tank level')}.")

        if user_account.has("fuel_research"):
            output.append(f"By having {user_account.write_count('fuel_research', 'level')} of fuel research, you can use {store.Fuel_Research.highest_gem[user_account.get('fuel_research')]} or any lower gem for making fuel.")

        if user_account.has("telescope_level"):
            output.append(f"With {user_account.write_count('telescope_level', 'telescope level')}, you can see in a {sn(user_account.get('telescope_level') * 2 + 5)} tile diameter area.")

        if user_account.has("advanced_exploration"):
            rr = user_account.get_recipe_refinement_multiplier()
            lcs = user_account.get(store.Loaf_Converter.name)
            multiplier = store.Advanced_Exploration.get_contribution(user_account.get(store.Advanced_Exploration.name))
            amount_pieces = user_account.get_anarchy_piece_luck((lcs + 1) * rr) - 1
            amount_gems = user_account.get_space_gem_luck((lcs + 1) * rr) - 1
            output.append(f"With {user_account.write_count('advanced_exploration', 'level')} of Advanced Exploration you have the following:")
            output.append(f"   {round(amount_pieces)} ({round(amount_pieces, 5)}, {round(multiplier * 100, 4)}%) of your Loaf Converters are used to find anarchy pieces.")
            output.append(f"   {utility.smart_number(round(amount_gems))} ({utility.smart_number(round(amount_gems, 5))}, {round(multiplier * 2500, 4)}%) of your Loaf Converters are used to find space gems.")

        if user_account.has("engine_efficiency"):
            level = user_account.get('engine_efficiency')
            output.append(f"You use {round((1 - store.Engine_Efficiency.consumption_multipliers[level]) * 100)}% less fuel with {user_account.write_count('engine_efficiency', 'level')} of Engine Efficiency.")

        if user_account.has("payment_bonus"):
            level = user_account.get('payment_bonus')
            output.append(f"You've recieved {utility.write_count(level, 'dubious bonus', 'e')} so far, and that gets you {utility.smart_number(int(level * store.Payment_Bonus.per_level))} more {values.project_credits.text} per day.")
            
        active_catalyst = store.find_catalyst(user_account.get("active_catalyst"))
        active_ephemerals = user_account.get_ephemeral_file()
        
        if active_catalyst is not None \
            or active_ephemerals \
            or user_account.get("lifetime_salvages") >= 1:
                output.extend([
                    "",
                    f"You can salvage items {user_account.write_count('salvage_remaining', 'more time')} today.",
                    f"You currently have the {active_catalyst.display_name} catalyst active for another {utility.write_count(user_account.get('catalyst_remaining'), 'salvage')}." if active_catalyst is not None else "You currently do not have a catalyst active.",
                    self.get_active_ephemeral_list(user_account)
                ])
        
        output.append("")
        output.append(f"Throughout your time in space you've created {utility.write_count(user_account.get('trade_hubs_created'), 'Trade Hub')} and helped contribute to {utility.write_count(user_account.get('projects_completed'), 'completed project')}.")

        # Add item amount information.
        item_list = [values.fuel, values.corrupted_bread, values.anarchy_chessatron, values.anarchy_omega_chessatron] + values.all_very_shinies

        item_line = []
        for item in item_list:
            if user_account.has(item.text):
                item_line.append(f"{user_account.get(item.text)} {item.text}")
        
        # Only show the item amount information if there is any information to show.
        if len(item_line) > 0:
            output.append("")
            output.append("Space items:")
            output.append(" , ".join(item_line))

        # Anarchy pieces.
        formatted_anarchy_pieces = self.format_anarchy_pieces(user_account.values).strip(" \n")

        if len("\n".join(output)) + len(formatted_anarchy_pieces) + 4 > 1900:
            await ctx.reply("\n".join(output))
            output = ["Stats continued:"]


        output.append("") # Add a blank item to add an extra new line.
        output.append(formatted_anarchy_pieces)

        await ctx.reply("\n".join(output))






        
        
        
    ########################################################################################################################
    #####      BREAD SPACE SHOP

    @bread.command(
        name = "space_shop",
        brief = "The Space Shop.",
        description = "Shortcut to '$bread space shop'.",
        aliases = ["space_store"],
        hidden = True
    )
    async def space_shop_shortcut(self, ctx):
        await ctx.invoke(self.space_shop)

    @space.command(
        name = "shop",
        brief = "The Space Shop.",
        aliases = ["store"]
    )
    async def space_shop(self, ctx):

        # first we make sure this is a valid channel
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Hello! Thanks for flying to the Space Shop. The nearest Space Shop Port is in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        # we get the account of the user who called it
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        # Make sure the player is on the right ascension.
        if user_account.get_prestige_level() < 1:
            await ctx.reply("The entrance to this shop is nowhere to be found, perhaps you need to ascend.")
            return
        
        # Temporarily lock all of space to a9 or higher. When a9 ends this should be removed.
        # if user_account.get_prestige_level() < 9:
        #     await ctx.reply("Currently the Space Shop is only available on the 9th ascension. When that ascension ends it will be available from the first ascension onwards.")
        #     return
        
        await self.shop_helper(
            ctx = ctx,
            user_account = user_account,
            buyable_list = store.space_shop_items,
            shop_name = "Space Shop"
        )
        
    ########################################################################################################################
    #####      BREAD SPACE MAP

    async def handle_map(
            self: typing.Self,
            ctx: commands.Context,
            map_type: str,
            user_account: account.Bread_Account,
            content: str = None,
            reduced_info: bool = False
        ) -> discord.Message:
        """Handles the process of generating the map and sending it to standardize how it's sent."""

        if content is None:
            content = ""
        if map_type is None:
            map_type = "system"
            
        dict_settings = {}
        
        other_settings = ctx.message.content.split(" " + map_type + " ", 1)[-1].split(" ")
            
        # Check to make sure the player is able to get the full map.
        if map_type == "full" or map_type == "f":
            hub_tile = user_account.get_system_tile(json_interface=self.json_interface) # type: space.SystemTradeHub

            if hub_tile.type != "trade_hub":
                return await ctx.reply("You currently do not have the ability to read and analyze map data from the communication network.\nBeing on a Trade Hub with the Offspring Outlook upgrade will allow you to read and analyze the data.")
            
            if hub_tile.get_upgrade_level(projects.Offspring_Outlook) < 1:
                return await ctx.reply("This Trade Hub doesn't have the required upgrades to be able to read and analyze the map data from the communication network.")
            
            try:
                if other_settings[0].lower() == "guide":
                    send_file = discord.File(space.MAP_GUIDE_BYTESIO, filename="map_guide.png")
                    return await ctx.reply(file=send_file)
            except IndexError:
                pass # If the setting was not provided a IndexError will be raised, which we can just ignore.

            full_x = None
            full_y = None
            
            try:
                full_x = parse_int(other_settings[0])
                full_y = parse_int(other_settings[1])
            except (ValueError, IndexError):
                pass # It failed to parse, so it's probably intended to be something.
            
            bubble_data = space.generate_trade_hub_bubbles(
                json_interface = self.json_interface,
                ascension = user_account.get_prestige_level(),
                guild = ctx.guild
            )
            
            if full_x is not None and full_y is not None:
                galaxy_x, galaxy_y = user_account.get_galaxy_location(json_interface=self.json_interface)
                
                if full_y < 0:
                    full_point = 1 >> (full_x + space.MAP_SIZE * abs(full_y))
                else:
                    full_point = 1 << (full_x + space.MAP_SIZE * full_y)
                
                # This `if` shouldn't ever trigger since you can't get the full map without being on a trade hub,
                # and trade hubs are always in the galaxy. But just in case, we'll check.
                if galaxy_y < 0:
                    current_point = 1 >> (galaxy_x + space.MAP_SIZE * abs(galaxy_y))
                else:
                    current_point = 1 << (galaxy_x + space.MAP_SIZE * galaxy_y)
                
                group = None
                
                for index, group_check in enumerate(bubble_data):
                    if group_check & current_point:
                        group = index
                        break
                
                if group is None:
                    # This should never be able to occur, but if it does then something has seriously gone wrong.
                    # If this somehow does happen, send a (hopefully) funny message and raise an exception to be looked at later.
                    await ctx.reply("You are nowhere.")
                    raise TypeError(f"Hub bubble group is None for {galaxy_x, galaxy_y} when it shouldn't be.")
                
                if not bool(bubble_data[group] & full_point):
                    return await ctx.reply("That point is not available in the current range of the communication network.")
            
                if not space.has_seen_tile(
                        json_interface = self.json_interface,
                        guild = ctx.guild,
                        ascension = user_account.get_prestige_level(),
                        xpos = full_x,
                        ypos = full_y
                    ):
                    return await ctx.reply("That is in range of the communication network, however nobody has seen what is there and the communication network does not have the missing information.")
            
            # If we're going through with doing the map, set the dictionary data.    
            dict_settings["bubble_data"] = bubble_data

        ###############################
        before = time.time()

        map_data = space.space_map(
            account = user_account,
            json_interface = self.json_interface,
            mode = map_type,
            other_settings = other_settings,
            dict_settings = dict_settings
        )

        after = time.time()
        ###############################

        corruption_chance = round(user_account.get_corruption_chance(json_interface=self.json_interface) * 100, 2)
        apiece_corruption_chance = round(user_account.get_anarchy_corruption_chance(json_interface=self.json_interface) * 100, 2)

        suffix = ""

        if map_type == "galaxy" or map_type == "g":
            prefix = "Galaxy map:"
            middle = f"Your current galaxy location: {user_account.get_galaxy_location(json_interface=self.json_interface)}.\nYour corruption chance: {corruption_chance}%."

            if not reduced_info:
                suffix = "You can use '$bread space map' to view the map for the system you're in.\n\nUse '$bread space move galaxy' to move around on this map."
        elif map_type == "full" or map_type == "f":
            analyze_x = None
            analyze_y = None
            
            if len(other_settings) >= 4:
                try:
                    analyze_x = parse_int(other_settings[2])
                    analyze_y = parse_int(other_settings[3])
                except ValueError:
                    pass # It failed to parse, so it's probably intended to be something.
            
            if full_x is not None and full_y is not None:
                highlighted_corruption = round(space.get_corruption_chance(full_x - space.MAP_RADIUS, full_y - space.MAP_RADIUS) * 100, 2)
                
                if analyze_x is not None and analyze_y is not None:
                    galaxy_seed = self.json_interface.get_ascension_seed(
                        ascension_id = user_account.get_prestige_level(),
                        guild = ctx.guild
                    )
                    
                    galaxy_tile = space.get_galaxy_coordinate(
                        json_interface = self.json_interface,
                        guild = ctx.guild,
                        galaxy_seed = galaxy_seed,
                        ascension = user_account.get_prestige_level(),
                        xpos = full_x,
                        ypos = full_y,
                        load_data = True
                    )
                    
                    if galaxy_tile.system:
                        analyze_point = galaxy_tile.get_system_tile(
                            json_interface = self.json_interface,
                            system_x = analyze_x,
                            system_y = analyze_y
                        )
                        
                        analysis_lines = analyze_point.get_analysis(
                            guild = ctx.guild,
                            json_interface = self.json_interface,
                            user_account = user_account,
                            detailed = True # Full analysis is always detailed.
                        )
                    else:
                        analysis_lines = ["There is nothing here."]
                        
                    line_emoji = ":arrow_forward:"

                    for index, item in enumerate(analysis_lines):
                        analysis_lines[index] = f"{line_emoji} {item}"
                        
                    prefix = "Full system analysis:"
                    middle = f"Your current galaxy location: {user_account.get_galaxy_location(json_interface=self.json_interface)}.\nYour corruption chance: {corruption_chance}%.\nHighlighted system: ({full_x}, {full_y})\nHighlighted corruption chance: {highlighted_corruption}%.\nHighlighted point: ({analyze_x}, {analyze_y})"
                    
                    suffix = "Analysis:\n" + "\n".join(analysis_lines)
                else:
                    prefix = "Full system map:"
                    middle = f"Your current galaxy location: {user_account.get_galaxy_location(json_interface=self.json_interface)}.\nYour corruption chance: {corruption_chance}%.\nHighlighted system: ({full_x}, {full_y})\nHighlighted corruption chance: {highlighted_corruption}%."
                    
                    suffix = f"Use '$bread space map full {full_x} {full_y} <system x> <system y>' to analyze a point within this system.\nUse '$bread space map full guide' to see a color guide."
            else:
                prefix = "Full galaxy map:"
                middle = f"Your current galaxy location: {user_account.get_galaxy_location(json_interface=self.json_interface)}.\nYour corruption chance: {corruption_chance}%."
            
                suffix = "Use '$bread space map full <galaxy x> <galaxy y>' to view a specific system.\nUse '$bread space map full guide' to see a color guide."
        else:
            prefix = "System map:"
            middle = f"Your current galaxy location: {user_account.get_galaxy_location(json_interface=self.json_interface)}.\nYour current system location: {user_account.get_system_location()}.\nYour corruption chance: {corruption_chance}%.\nAnarchy Piece corruption chance: {apiece_corruption_chance}%."
            
            if not reduced_info:
                suffix = "You can use '$bread space map galaxy' to view the galaxy map.\n\nUse '$bread space move system' to move around on this map.\nUse '$bread space analyze' to get more information about somewhere."

        send_file = discord.File(map_data, filename="space_map.png")
        file_path = "attachment://space_map.png"

        embed = discord.Embed(
            title = prefix,
            description = middle + "\n\n" + suffix,
            color=8884479,
        )
        embed.set_image(url=file_path)
        embed.set_footer(text=f"Map generated in {round(after - before, 3)} seconds.")

        return await ctx.reply(content, embed=embed, file=send_file)


    @bread.command(
        name = "map",
        aliases = ["view"],
        brief = "View the space map.",
        description = "View the space map.\nYou can use the 'galaxy' mode to view the galaxy map."
    )
    async def bread_map(self, ctx,
            mode: typing.Optional[str] = commands.parameter(description="The map mode to use.")
        ):
        await self.space_map(ctx, mode)
    
    @space.command(
        name = "map",
        aliases = ["view"],
        brief = "View the space map.",
        description = "View the space map.\nYou can use the 'galaxy' mode to view the galaxy map."
    )
    async def space_map(self, ctx,
            mode: typing.Optional[str] = commands.parameter(description="The map mode to use.")
        ):
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_BASIC:
            await ctx.reply(f"I appreciate your interest in the space map! You can find the telescopes in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        if user_account.get_space_level() < 1:
            await ctx.reply("You do not yet have a rocket that can help you map the vast reaches of space.\nYou can purchase the required rocket from the Space Shop.")
            return
        
        await self.handle_map(
            ctx = ctx,
            map_type = mode,
            user_account = user_account,
            content = None # So it includes nothing else in the message.
        )
        
    ########################################################################################################################
    #####      BREAD SPACE ANALYZE

    @bread.command(
        name = "analyze",
        aliases = ["analyse", "analysis", "scan"],
        brief = "Analyze and get information about planets.",
        description = "Analyze and get information about planets.\n\nTo get a guide for the point parameter, look at the system map."
    )
    async def bread_analyze(self, ctx,
            point: typing.Optional[str] = commands.parameter(description="The point around you to analyze.")
        ):
        await self.space_analyze(ctx, point)
    
    @space.command(
        name = "analyze",
        aliases = ["analyse", "analysis", "scan"],
        brief = "Analyze and get information about planets.",
        description = "Analyze and get information about planets.\n\nTo get a guide for the point parameter, look at the system map."
    )
    async def space_analyze(self, ctx,
            point: typing.Optional[str] = commands.parameter(description="The point around you to analyze.")
        ):
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Thank you for trying to analyze a system! The nearest science center is in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        if user_account.get_space_level() < 1:
            await ctx.reply("You do not yet have a rocket that can help you analyze the many celestial objects in space.\nYou can purchase the required rocket from the Space Shop.")
            return
        
        ##########################################################
        ##### Ensuring the arguments are properly passed.
        
        HELP_MSG = "You must provide the point to analyze in the form of '<letter><number>'.\nYou can find a guide in the system map."
        detailed = False

        telescope_level = user_account.get("telescope_level")
        radius = telescope_level + 2
        diameter = radius * 2 + 1

        letters = "abcdefghijklmnopqrstuvwxyz"
        
        if point is None:
            point = f"{letters[radius]}{radius + 1}"
            detailed = True
        elif point == f"{letters[radius]}{radius + 1}":
            detailed = True

        
        if telescope_level >= 3:
            if not(2 <= len(point) <= 3):
                await ctx.reply(HELP_MSG)
                return
        else:
            if len(point) != 2:
                await ctx.reply(HELP_MSG)
                return

        pattern = "([a-{letter_end}])([{number_start}-{number_end}]{{1,{times}}})".format(
            letter_end = letters[diameter - 1],
            number_start = 1 if diameter < 10 else 0,
            number_end = min(diameter, 9),
            times = len(str(diameter))
        )
        
        matched = re.match(pattern, point.lower())

        if matched is None:
            await ctx.reply(HELP_MSG)
            return
        
        x_modifier = letters.index(matched.group(1).lower()) # group 1 is the letter.
        y_modifier = int(matched.group(2).lower()) - 1 # group 2 is the number.

        if round(math.hypot(abs(x_modifier - radius), abs(y_modifier - radius))) > radius:
            await ctx.reply("You cannot see that point.")
            return
        
        ##########################################################
        ##### Generating the map.
        before = time.time()

        map_path = space.space_map(
            account = user_account,
            json_interface = self.json_interface,
            mode = "system",
            analyze_position = point.lower()
        )

        after = time.time()
        ##########################################################
        ##### Getting the analysis data.

        galaxy_x, galaxy_y = user_account.get_galaxy_location(json_interface=self.json_interface)

        system_data = space.get_galaxy_coordinate(
            json_interface = self.json_interface,
            guild = ctx.guild.id,
            galaxy_seed = self.json_interface.get_ascension_seed(user_account.get_prestige_level(), guild=user_account.get("guild_id")),
            ascension = user_account.get_prestige_level(),
            xpos = galaxy_x,
            ypos = galaxy_y,
            load_data = False
        )

        player_x, player_y = user_account.get_system_location()

        if system_data.system:
            tile_x = x_modifier - radius + player_x
            tile_y = y_modifier - radius + player_y

            if detailed:
                if tile_x != player_x or tile_y != player_y:
                    await ctx.reply("Your scientific sensors are unable to get a detailed report of celestial bodies you're not on top of.")
                    return

            tile_analyze = system_data.get_system_tile(
                json_interface = self.json_interface,
                system_x = tile_x,
                system_y = tile_y
            )

            analysis_lines = tile_analyze.get_analysis(
                guild = ctx.guild.id,
                json_interface = self.json_interface,
                user_account = user_account,
                detailed = detailed
            )
        else:
            analysis_lines = ["There is nothing here."]

        line_emoji = ":arrow_forward:"

        for index, item in enumerate(analysis_lines):
            analysis_lines[index] = f"{line_emoji} {item}"
        
        analysis_lines.append(line_emoji)
        analysis_lines.append(f"{line_emoji} Analysis footer:")
        analysis_lines.append(f"{line_emoji} Move command:")
        analysis_lines.append(f"{line_emoji} $bread space move system {point} y")

        ##########################################################        
        ##### Sending the message.

        send_file = discord.File(map_path, filename="space_map.png")
        file_path = "attachment://space_map.png"

        embed_send = discord.Embed(
            title = "Tile Analysis",
            description = "\n".join(analysis_lines),
            color=8884479,
        )
        embed_send.set_image(url=file_path)
        embed_send.set_footer(text=f"Analysis generated in {round(after - before, 3)} seconds.")
        
        await ctx.reply(embed=embed_send, file=send_file)







        
    ########################################################################################################################
    #####      BREAD SPACE HUB
    
    async def trade_hub_contribute_level(
            self: typing.Self,
            ctx: commands.Context,
            user_account: account.Bread_Account,
            day_seed: str,
            hub_projects: list[dict],
            hub: space.SystemTradeHub,
            actions: tuple[str],

            galaxy_x: int,
            galaxy_y: int,

            item: values.Emote,
            amount: int
        ) -> None:
        """Contributes items to a trade hub level."""
        level_messages = {
            2: f"This Trade Hub is now able to relay trade signals from the Trade Hub network up to {store.trade_hub_distances[2]} tiles away!",
            3: f"This Trade Hub now has {store.trade_hub_projects[3]} project slots!",
            4: f"This Trade Hub is now able to relay trade signals from the Trade Hub network up to {store.trade_hub_distances[4]} tiles away!",
            5: f"This Trade Hub now has {store.trade_hub_projects[5]} project slots!",
        }
        
        level_project = projects.Trade_Hub
        max_level = len(level_project.all_costs())

        if hub.trade_hub_level == max_level:
            await ctx.reply("This Trade Hub is already at the max level!")
            return

        ascension_data = self.json_interface.get_space_ascension(
            ascension_id = user_account.get_prestige_level(),
            guild = ctx.guild.id
        )

        all_trade_hubs = ascension_data.get("trade_hubs", dict())
        trade_hub_data = all_trade_hubs.get(f"{galaxy_x} {galaxy_y}", dict())

        level_progress = trade_hub_data.get("level_progress", dict())

        remaining = level_project.get_remaining_items(
            day_seed = day_seed,
            system_tile = hub,
            progress_data = level_progress
        )
        
        if amount == "full":
            # Contributing everything is handled separately, since it contributes all of the items.
            
            required_description = level_project.get_remaining_description(
                day_seed = day_seed,
                system_tile = hub,
                progress_data = level_progress
            )
            
            self.currently_interacting.append(ctx.author.id)
            # Item is the confirmation, so treat it as such.
            if not item:
                message = [f"To level up the Trade Hub, you have the following items out of what is needed:\n"]
                
                for item_iter, amount in remaining.items():
                    message.append(f"{item_iter}: {utility.smart_number(user_account.get(item_iter))}/{utility.smart_number(amount)}")
                
                message.append("\nWould you like to contribute all of these items to level up the Trade Hub? Yes or no.")
                
                confirm_text = ["yes", "y", "confirm"]
                cancel_text = ["no", "n", "cancel"]

                await ctx.reply("\n".join(message))
                    
                def check(m: discord.Message):
                    return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id 

                try:
                    msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
                except asyncio.TimeoutError: 
                    await ctx.reply("I'm sorry, but you have taken too long and I must attend to the next customer.")
                    self.remove_from_interacting(ctx.author.id)
                    return
                
                if msg.content.lower() in cancel_text:
                    await ctx.reply("Very well, come back when you would like to level up the Trade Hub.")

                    self.remove_from_interacting(ctx.author.id)
                    return
                elif msg.content.lower() not in confirm_text:
                    await ctx.reply("I'm not entirely sure what that is, please try again.")

                    self.remove_from_interacting(ctx.author.id)
                    return
            
            # If it gets to this point that means it's time to attempt to level up the Trade Hub.
            
            for item_iter, amount in remaining.items():
                if user_account.get(item_iter) < amount:
                    await ctx.reply(f"You do not have enough {item_iter} to level up the Trade Hub.")
                    self.remove_from_interacting(ctx.author.id)
                    return

                user_account.increment(item_iter, -amount)
                
            existing = self.json_interface.get_trade_hub_data(
                guild = ctx.guild.id,
                ascension = user_account.get_prestige_level(),
                galaxy_x = galaxy_x,
                galaxy_y = galaxy_y
            )
            
            if existing.get("level", 0) >= 5:
                await ctx.reply("This Trade Hub is already at the max level!")
                self.remove_from_interacting(ctx.author.id)
                return
            
            self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)

            await ctx.reply("You have contributed {used} to level up the Trade Hub.\nYou now have {remaining} remaining.".format(
                used = required_description,
                remaining = " , ".join([f"**{utility.smart_number(user_account.get(item_iter))}** {item_iter}" for item_iter in remaining.keys()])
            ))

            if "level" in existing:
                existing["level"] += 1
            else:
                # If the key doesn't exist, then we know it's a natural one.
                # All natural trade hubs have a level of 1, so update it to 2.
                existing["level"] = 2

            # Reset the progress dict.
            existing["level_progress"] = {}
            
            self.json_interface.update_trade_hub_data(
                guild = ctx.guild.id,
                ascension = user_account.get_prestige_level(),
                galaxy_x = galaxy_x,
                galaxy_y = galaxy_y,
                new_data = existing
            )
            
            message = level_messages[existing["level"]]

            send_lines = f"Trade Hub levelled up to level {existing['level']}! {message}"
            send_lines += level_project.completion(day_seed, hub)

            send_lines += "\n\n"
            for player_id in list(level_progress.keys()) + [ctx.author.id]:
                send_lines += f"<@{player_id}> "
                
            await asyncio.sleep(1)

            await ctx.send(send_lines)
            self.remove_from_interacting(ctx.author.id)
            return
    
        if item.text not in remaining:
            await ctx.reply("We don't need any more of that to level up the Trade Hub.")
            self.remove_from_interacting(ctx.author.id)
            return
        
        if amount == "all":
            amount = user_account.get(item.text)
    
        amount_contribute = min(remaining[item.text], amount)

        player_data = level_progress.get(str(ctx.author.id), {"items": {}})
        
        user_account.increment(item.text, -amount_contribute)

        if item.text in player_data["items"]:
            player_data["items"][item.text] += amount_contribute
        else:
            player_data["items"][item.text] = amount_contribute
        
        level_progress[str(ctx.author.id)] = player_data

        self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)

        self.json_interface.update_trade_hub_levelling_data(
            guild = ctx.guild.id,
            ascension = user_account.get_prestige_level(),
            galaxy_x = galaxy_x,
            galaxy_y = galaxy_y,
            new_data = level_progress
        )

        amount_left = user_account.get(item.text)
        
        await ctx.reply(f"You have contributed {utility.smart_number(amount_contribute)} {item.text} to levelling up the Trade Hub!\nYou now have {utility.smart_number(amount_left)} {item.text} remaining.")

        # Check for completion.

        remaining = level_project.get_remaining_items(
            day_seed = day_seed,
            system_tile = hub,
            progress_data = level_progress
        )

        if len(remaining) != 0:
            # No completion :(
            self.remove_from_interacting(ctx.author.id)
            return

        existing = self.json_interface.get_trade_hub_data(
            guild = ctx.guild.id,
            ascension = user_account.get_prestige_level(),
            galaxy_x = galaxy_x,
            galaxy_y = galaxy_y
        )

        if "level" in existing:
            existing["level"] += 1
        else:
            # If the key doesn't exist, then we know it's a natural one.
            # All natural trade hubs have a level of 1, so update it to 2.
            existing["level"] = 2

        # Reset the progress dict.
        existing["level_progress"] = {}
        
        self.json_interface.update_trade_hub_data(
            guild = ctx.guild.id,
            ascension = user_account.get_prestige_level(),
            galaxy_x = galaxy_x,
            galaxy_y = galaxy_y,
            new_data = existing
        )
        
        message = level_messages[existing["level"]]

        send_lines = f"Trade Hub levelled up to level {existing['level']}! {message}"
        send_lines += level_project.completion(day_seed, hub)

        send_lines += "\n\n"
        for player_id in level_progress.keys():
            send_lines += f"<@{player_id}> "
            
        await asyncio.sleep(1)

        await ctx.send(send_lines)
        return
        







    ##############################################################################################################
        
    async def trade_hub_contribute(
            self: typing.Self,
            ctx: commands.Context,
            user_account: account.Bread_Account,
            day_seed: str,
            hub_projects: list[dict],
            hub: space.SystemTradeHub,
            actions: tuple[str]
        ) -> None:
        """Contributes items to a trade hub project, or the trade hub level."""
        if ctx.author.id in self.currently_interacting:
            return
        
        galaxy_x, galaxy_y = user_account.get_galaxy_location(json_interface=self.json_interface, correct_center=True)

        actions += [" ", " ", " ", " "]
        
        project_number = None
        try:
            if actions[1] == "level":
                project_number = "level"
            else:
                project_number = parse_int(actions[1])

            if actions[2] == "all":
                amount = "all"
            elif actions[2] == "full" and project_number == "level":
                amount = "full"
            else:
                amount = parse_int(actions[2])

            if actions[2] == "full":
                # If the amount is full, then the item is not needed and the confirmation goes in its slot.
                # This also means that the confirmation is passed to the level contribution, which it wouldn't do otherwise.
                item = actions[3].lower() in ["yes", "y", "confirm"]
            else:
                item = values.get_emote(actions[3])
                
            confirmation = actions[4].lower() in ["yes", "y", "confirm"]
        except ValueError:
            if project_number == "level":
                await ctx.reply("To help level up the Trade Hub, use this format:\n'$bread space hub contribute level [amount] [item]' to contribute a single type of item, or '$bread space hub contribute level full' to contribute all required items.")
            else:
                await ctx.reply("To contribute to a project, use this format:\n'$bread space hub contribute [project number] [amount] [item]'")
            return

        if item is None:
            if project_number == "level":
                await ctx.reply("To help level up the Trade Hub, use this format:\n'$bread space hub contribute level [amount] [item]' to contribute a single type of item, or '$bread space hub contribute level full' to contribute all required items.")
            else:
                await ctx.reply("To contribute to a project, use this format:\n'$bread space hub contribute [project number] [amount] [item]'")
            return
        
        if amount != "all" and not(amount == "full" and project_number == "level"):
            if amount < 0:
                await ctx.reply("Hey there, are you trying to steal resources?\nThat's kind of rude.")
                await ctx.invoke(self.bot.get_command('brick'), member=ctx.author)
                return
            
            if amount == 0:
                await ctx.reply("Congratulations, you have done absolutely nothing. I will now take your spleen.")
                return
            
            if amount > user_account.get(item.text):
                await ctx.reply("You don't have enough of that to contribute.")
                return
        
        if project_number == "level":
            await self.trade_hub_contribute_level(
                ctx = ctx,
                user_account = user_account,
                day_seed = day_seed,
                hub_projects = hub_projects,
                hub = hub,
                actions = actions,
                galaxy_x = galaxy_x,
                galaxy_y = galaxy_y,
                item = item,
                amount = amount
            )
            return

        if not (1 <= project_number <= hub.project_count):
            await ctx.reply("That is an unrecognized project number.")
            return
        
        project_data = hub_projects[project_number - 1]

        if project_data.get("completed", False):
            await ctx.reply("This project has already been completed.")
            return
        
        project = project_data.get("project") # type: projects.Project

        remaining = project.get_remaining_items(
            day_seed = day_seed,
            system_tile = hub,
            progress_data = project_data.get("contributions", {})
        )

        if len(remaining) == 0:
            out_data = {
                "internal": project.internal,
                "completed": True,
                "contributions": project_data.get("contributions")
            }
            
            self.json_interface.update_project_data(
                guild = ctx.guild.id,
                ascension = user_account.get_prestige_level(),
                galaxy_x = galaxy_x,
                galaxy_y = galaxy_y,
                project_id = project_number,
                new_data = out_data
            )

            await ctx.reply("This project has already been completed.")
            return
        
        if item.text not in remaining:
            await ctx.reply("The project doesn't need any more of that item.")
            return
        
        total_required = project.total_items_required(day_seed, hub)

        if amount == "all":
            percentage_left = user_account.get("hub_credits") / 2000
            amount = math.ceil(((percentage_left + math.sqrt(percentage_left ** 2 + 4 * percentage_left)) / 2) * total_required)
        
        amount_contribute = min(remaining[item.text], amount, user_account.get(item.text))

        contribution_data = project_data.get("contributions", [])

        player_data = contribution_data.get(str(ctx.author.id), {"items": {}})

        # Make sure the player has the credits to contribute this.
        prior_items = sum(player_data["items"].values())

        total_credits_used = space.get_project_credits_usage(
            total_items = total_required,
            items_contributed = amount_contribute,
            item_offset = prior_items
        )

        old_credits_used = space.get_project_credits_usage(
            total_items = total_required,
            items_contributed = prior_items
        )

        credits_used = total_credits_used - old_credits_used

        remaining_credits = user_account.get("hub_credits")

        if remaining_credits < credits_used:
            await ctx.reply(f"You don't have enough {values.project_credits.text} to contribute that.")
            return

        ##########
        # Ask for confirmation.

        project_name = project.name(day_seed, hub)

        if not confirmation:
            self.currently_interacting.append(ctx.author.id)
            
            confirm_text = ["yes", "y", "confirm"]
            cancel_text = ["no", "n", "cancel"]

            await ctx.reply(f"You are contributing {utility.smart_number(amount_contribute)} {item.text} to the {project_name} project.\nThis will require {utility.smart_number(credits_used)} {values.project_credits.text}.\nYou currently have the following:\n- {utility.smart_number(user_account.get(item.text))} {item.text}\n- {utility.smart_number(user_account.get('hub_credits'))} {values.project_credits.text}\nWould you like to go through with your confirmation? Yes or No.")
                
            def check(m: discord.Message):
                return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id 

            try:
                msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
            except asyncio.TimeoutError: 
                await ctx.reply("I'm sorry, but you have taken too long and I must attend to the next customer.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            if msg.content.lower() in cancel_text:
                await ctx.reply("Very well, come back when you would like to contribute.")

                self.remove_from_interacting(ctx.author.id)
                return
            elif msg.content.lower() not in confirm_text:
                await ctx.reply("I'm not entirely sure what that is, please try again.")

                self.remove_from_interacting(ctx.author.id)
                return
            
            self.remove_from_interacting(ctx.author.id)



        ##########
        # Going through with contributing.
        
        # Refresh the project data in case anything has changed between when it originally was fetched.
        # Two people contributing at the same time can cause this to be the case.
        hub_projects = space.get_trade_hub_projects(
            json_interface = self.json_interface,
            user_account = user_account,
            system_tile = hub
        )
        project_data = hub_projects[project_number - 1]
        
        if project_data.get("completed", False):
            await ctx.reply("This project has already been completed.")
            return
        
        project = project_data.get("project") # type: projects.Project
        contribution_data = project_data.get("contributions", [])
        player_data = contribution_data.get(str(ctx.author.id), {"items": {}})

        user_account.increment("hub_credits", -credits_used)
        
        user_account.increment(item.text, -amount_contribute)

        if item.text in player_data["items"]:
            player_data["items"][item.text] += amount_contribute
        else:
            player_data["items"][item.text] = amount_contribute
        
        contribution_data[str(ctx.author.id)] = player_data

        out_data = {
            "internal": project.internal,
            "completed": False,
            "contributions": contribution_data
        }

        self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)
        self.json_interface.update_project_data(
            guild = ctx.guild.id,
            ascension = user_account.get_prestige_level(),
            galaxy_x = galaxy_x,
            galaxy_y = galaxy_y,
            project_id = project_number,
            new_data = out_data
        )

        amount_left = user_account.get(item.text)
        
        await ctx.reply(f"You have contributed {utility.smart_number(amount_contribute)} {item.text} to the {project_name} project.\nYou now have {utility.smart_number(amount_left)} {item.text} and {utility.smart_number(user_account.get('hub_credits'))} {values.project_credits.text} remaining.")

        updated_required = project.get_remaining_items(
            day_seed = day_seed,
            system_tile = hub,
            progress_data = out_data.get("contributions", {})
        )
        if len(updated_required) != 0:
            # It hasn't been completed. :(
            return
        
        ########################################
        # It's been completed! :o

        out_data["completed"] = True

        self.json_interface.update_project_data(
            guild = ctx.guild.id,
            ascension = user_account.get_prestige_level(),
            galaxy_x = galaxy_x,
            galaxy_y = galaxy_y,
            project_id = project_number,
            new_data = out_data
        )

        send_lines = "Project completed!\n\n"
        send_lines += project.completion(day_seed, hub)
        send_lines += "\n\nIndividual earnings:"

        total_items = project.total_items_required(day_seed, hub)
        reward = project.get_reward(day_seed, hub)

        for player_id, contributions in out_data.get("contributions", {}).items():
            items = contributions.get("items", {})

            items_contributed = sum(items.values())

            percent_cut = items_contributed / total_items

            player_account = self.json_interface.get_account(player_id, guild=ctx.guild.id)

            items_added = []

            for win_item, win_amount in reward:
                amount = math.ceil(win_amount * percent_cut)
                player_account.increment(win_item, amount)

                items_added.append(f"{utility.smart_number(amount)} {win_item}")

            player_account.increment("projects_completed", 1)

            self.json_interface.set_account(player_id, player_account, guild = ctx.guild.id)
            
            send_lines += f"\n- <@{player_id}>: {' ,  '.join(items_added)}"
        
        await asyncio.sleep(1)

        await ctx.send(send_lines)
        return

    ##############################################################################################################
        
    async def trade_hub_info(
            self: typing.Self,
            ctx: commands.Context,
            user_account: account.Bread_Account,
            day_seed: str,
            hub_projects: list[dict],
            hub: space.SystemTradeHub,
            actions: tuple[str]
        ) -> None:
        """Gets information about a project and sends it."""
        actions.append(" ")

        try:
            project_number = parse_int(actions[1])
        except ValueError:
            await ctx.reply("To get information about a project, use '$bread space hub info [project number]'")
            return
        
        if not (1 <= project_number <= hub.project_count):
            await ctx.reply("That is an unrecognized project number.")
            return
        
        project_data = hub_projects[project_number - 1]
        project = project_data.get("project")

        contributions = project_data.get('contributions')
        amount_contributed = project.total_items_collected(day_seed, hub, contributions)
        amount_needed = project.total_items_required(day_seed, hub)

        message_lines = f"# -- Project {project.name(day_seed, hub)}: --"
        message_lines += f"\n{project.description(day_seed, hub)}"
        message_lines += f"\n\nCompleted: {':white_check_mark:' if project_data.get('completed', False) else ':x:'}"
        message_lines += "\nCollected items: {have}/{total} ({percent}%)".format(
            have = utility.smart_number(amount_contributed),
            total = utility.smart_number(amount_needed),
            percent = round(100 * project.get_progress_percent(day_seed, hub, contributions), 2)
        )
        if amount_contributed != amount_needed:
            message_lines += f"\nRemaining items:\n{project.get_remaining_description(day_seed, hub, contributions)}"

        if amount_contributed > 0:
            message_lines += f"\nIndividual contributions:"

            for player_id, data in project_data.get("contributions", {}).items():
                player_account = self.json_interface.get_account(player_id, guild=ctx.guild.id)

                player_line = []

                for item, amount in data.get("items", {}).items():
                    player_line.append(f"{amount} {item}")

                username = utility.sanitize_ping(player_account.get_display_name())
                player_line = " ,  ".join(player_line)
                
                message_lines += f"\n- {username}: {player_line}"
        
        if amount_contributed != amount_needed:
            message_lines += f"\n\nTo contribute to this project, use '$bread space hub contribute {project_number} [amount] [item]'."
        
        if len(message_lines) <= 1950:
            await ctx.reply(message_lines)
        else:
            # If the message is too long split it by sentences and send each piece.
            
            split = message_lines.split(".")
            
            send = []
            current = ""
            
            for sentence in split:
                if len(current) + len(sentence) < 1950:
                    current += sentence + "."
                else:
                    send.append(current)
                    current = sentence + "."
            
            send.append(current)
            
            for part in send:
                await ctx.reply(part)



    ##############################################################################################################
    
    async def trade_hub_level(
            self: typing.Self,
            ctx: commands.Context,
            user_account: account.Bread_Account,
            day_seed: str,
            hub_projects: list[dict],
            hub: space.SystemTradeHub,
            actions: tuple[str]
        ) -> None:
        """Gets information about the trade hub levelling and sends it."""
        galaxy_x, galaxy_y = user_account.get_galaxy_location(json_interface=self.json_interface, correct_center=True)
        level_project = projects.Trade_Hub
        max_level = len(level_project.all_costs())

        if hub.trade_hub_level == max_level:
            await ctx.reply("This Trade Hub is already at the max level!")
            return

        ascension_data = self.json_interface.get_space_ascension(
            ascension_id = user_account.get_prestige_level(),
            guild = ctx.guild.id
        )

        all_trade_hubs = ascension_data.get("trade_hubs", dict())
        trade_hub_data = all_trade_hubs.get(f"{galaxy_x} {galaxy_y}", dict())
        
        message_lines = "# -- Trade Hub Levelling --"
        message_lines += f"\nCurrent Trade Hub level: {hub.trade_hub_level}"
        message_lines += f"\nRemaining items:"

        level_progress = trade_hub_data.get("level_progress", dict())
        cost = dict(level_project.get_cost(day_seed, hub))
        remaining = level_project.get_remaining_items(day_seed, hub, level_progress)

        sn = utility.smart_number

        for item, amount in cost.items():
            left = remaining.get(item, 0)
            contributed = amount - left
            message_lines += f"\n- {item}: {sn(contributed)}/{sn(amount)} ({round(contributed / amount * 100, 2)}%)"

        amount_contributed = level_project.total_items_collected(day_seed, hub, level_progress)
        amount_needed = level_project.total_items_required(day_seed, hub)

        message_lines += "\nCollected items: {have}/{total} ({percent}%)".format(
            have = sn(amount_contributed),
            total = sn(amount_needed),
            percent = round(100 * level_project.get_progress_percent(day_seed, hub, level_progress), 2)
        )

        if amount_contributed > 0:
            message_lines += f"\nIndividual contributions:"

            for player_id, data in level_progress.items():
                player_account = self.json_interface.get_account(player_id, guild=ctx.guild.id)

                player_line = []

                for item, amount in data.get("items", {}).items():
                    player_line.append(f"{sn(amount)} {item}")

                username = utility.sanitize_ping(player_account.get_display_name())
                player_line = " ,  ".join(player_line)
                
                message_lines += f"\n- {username}: {player_line}"
        
        if amount_contributed != amount_needed:
            message_lines += f"\n\nTo help level up this Trade Hub, use '$bread space hub contribute level [amount] [item]'."

        await ctx.reply(message_lines)
        return

    ##############################################################################################################
    
    async def trade_hub_upgrade_purchase(
            self: typing.Self,
            ctx: commands.Context,
            user_account: account.Bread_Account,
            day_seed: str,
            hub: space.SystemTradeHub,
            upgrade: projects.Trade_Hub_Upgrade
        ) -> None:
        if upgrade not in hub.get_available_upgrades(day_seed):
            await ctx.reply("Sorry, this Trade Hub already has as many of that upgrade as it can.")
            return

        if not upgrade.is_affordable_for(
            day_seed = day_seed,
            system_tile = hub,
            user_account = user_account
        ):
            await ctx.reply("Sorry, but you can't afford to buy that.")
            return
        
        upgrade.do_purchase(
            day_seed = day_seed,
            system_tile = hub,
            user_account = user_account
        )

        trade_hub_data = self.json_interface.get_trade_hub_data(
            guild = ctx.guild,
            ascension = user_account.get_prestige_level(),
            galaxy_x = hub.galaxy_xpos,
            galaxy_y = hub.galaxy_ypos
        )

        cost_types = upgrade.get_cost_types(
            day_seed = day_seed,
            system_tile = hub
        )

        all_upgrade_data = trade_hub_data.get("upgrades", {})
        upgrade_data = all_upgrade_data.get(upgrade.internal, {})

        if "level" in upgrade_data:
            upgrade_data["level"] += 1
        else:
            upgrade_data["level"] = 1

        new_level = upgrade_data["level"]
        
        all_upgrade_data[upgrade.internal] = upgrade_data
        trade_hub_data["upgrades"] = all_upgrade_data

        self.json_interface.update_trade_hub_data(
            guild = ctx.guild,
            ascension = user_account.get_prestige_level(),
            galaxy_x = hub.galaxy_xpos,
            galaxy_y = hub.galaxy_ypos,
            new_data = trade_hub_data
        )

        self.json_interface.set_account(
            user = ctx.author,
            user_account = user_account,
            guild = ctx.guild
        )

        completion = upgrade.completion(
            day_seed = day_seed,
            system_tile = hub
        )

        await ctx.reply(f"The Trade Hub now has a level {utility.smart_number(new_level)} {upgrade.name(day_seed, hub)}!\n{completion}\n\nYou now have {', '.join([f'**{utility.smart_number(user_account.get(item))}** {item}' for item in cost_types])} remaining.")


    
    async def trade_hub_upgrades(
            self: typing.Self,
            ctx: commands.Context,
            user_account: account.Bread_Account,
            day_seed: str,
            hub_projects: list[dict],
            hub: space.SystemTradeHub,
            actions: tuple[str]
        ) -> None:
        """Lists all available upgrades to the given Trade Hub."""

        # Check if the user is trying to purchase an upgrade.
        potential_name = " ".join(actions[1:]).lower()

        for upgrade in projects.all_trade_hub_upgrades:
            if upgrade.name(day_seed, hub).lower() == potential_name or upgrade.internal.lower() == potential_name:
                await self.trade_hub_upgrade_purchase(
                    ctx = ctx,
                    user_account = user_account,
                    day_seed = day_seed,
                    hub = hub,
                    upgrade = upgrade
                )
                return
        
        ###############
        # If no upgrades were found, list available upgrades.

        name = generation.get_trade_hub_name(
            galaxy_seed = self.json_interface.get_ascension_seed(user_account.get_prestige_level(), guild=user_account.get("guild_id")),
            galaxy_x = hub.galaxy_xpos,
            galaxy_y = hub.galaxy_ypos
        )

        message_lines = f"Available upgrades for Trade Hub {name}:\nAll upgrades are for the Trade Hub, and anyone can use them.\n\n"

        listed = 0

        for upgrade in hub.get_available_upgrades(day_seed):
            old_message = message_lines

            add = f"\t**{upgrade.name(day_seed, hub)}** - {upgrade.get_price_description(day_seed, hub)}\n{upgrade.description(day_seed, hub)}\n\n"

            message_lines += add

            if len(message_lines) > 1900:
                await ctx.reply(old_message)
                message_lines = f"Continued:\n\n{add}"
            
            listed += 1
        
        if listed == 0:
            message_lines += "*Nothing is available.*\n\n"
        
        message_lines += "Use '$bread space hub upgrade <upgrade name>` to purchase that upgrade."

        purchased = hub.get_purchased_upgrades()

        if len(purchased) > 0:
            message_lines += "\n\nAlready purchased upgrades:"
            for upgrade in purchased:
                old_message = message_lines

                add = "\n- {} level {}: {}".format(
                    upgrade.name(day_seed, hub),
                    hub.get_upgrade_level(upgrade),
                    upgrade.purchased_description(day_seed, hub).replace('\n',' ') # .format is needed here due to the `\n`.
                )

                message_lines += add

                if len(message_lines) > 1900:
                    await ctx.reply(old_message)
                    message_lines = f"Continued:\n\n{add}"

        await ctx.reply(message_lines)
    
    async def trade_hub_configure_beacon(
            self: typing.Self,
            ctx: commands.Context,
            user_account: account.Bread_Account,
            day_seed: str,
            hub_projects: list[dict],
            hub: space.SystemTradeHub,
            actions: tuple[str]
        ) -> None:
        """Trade Hub configuration, specifically the Shroud Beacon."""
        if hub.get_upgrade_level(projects.Shroud_Beacon) < 1:
            await ctx.reply("There is nothing to configure.")
            return
        
        all_configuration = space.get_trade_hub_project_categories(day_seed, hub)

        if len(actions) >= 3:
            if actions[2].lower() in all_configuration or actions[2].lower() == "none":
                new_state = actions[2].lower()

                if new_state == "none":
                    new_state = None

                # Configure this setting.
                trade_hub_data = self.json_interface.get_trade_hub_data(
                    guild = ctx.guild,
                    ascension = user_account.get_prestige_level(),
                    galaxy_x = hub.galaxy_xpos,
                    galaxy_y = hub.galaxy_ypos
                )

                settings = trade_hub_data.get("settings", {})
                settings["shroud_beacon_queue"] = new_state

                trade_hub_data["settings"] = settings

                self.json_interface.update_trade_hub_data(
                    guild = ctx.guild,
                    ascension = user_account.get_prestige_level(),
                    galaxy_x = hub.galaxy_xpos,
                    galaxy_y = hub.galaxy_ypos,
                    new_data = trade_hub_data
                )

                if new_state is None:
                    new_state = "no"

                await ctx.reply(f"The Shroud Beacon has been configured to prioritize {new_state} projects.\nThe beacon takes some time to charge up, though, so it will only take effect the next time projects change.")
                return
        
        await ctx.reply("To configure the Shroud Beacon use '$bread space hub configure beacon <setting>'\nCurrent configuration: {}\nQueued configuration: {}\nAvailable settings are as follows: '{}' or 'none' to disable it.".format(
            str(hub.get_setting("shroud_beacon_setting", None)).title(),
            str(hub.get_setting("shroud_beacon_queue", None)).title(),
            '\', \''.join(all_configuration.keys())
        ))
    
    async def trade_hub_configure_color(
            self: typing.Self,
            ctx: commands.Context,
            user_account: account.Bread_Account,
            day_seed: str,
            hub_projects: list[dict],
            hub: space.SystemTradeHub,
            actions: tuple[str]
        ) -> None:
        available_colors = list(space.HUB_STRING_TO_COLOR.keys())
        
        if len(actions) < 3 or actions[2].lower() not in available_colors:
            await ctx.reply(f"To change the color of this Trade Hub, use '$bread space hub configure color <color>'\nAvailable colors: {', '.join(available_colors)}")
            return
        
        chosen = actions[2].lower()
        color_code = space.HUB_STRING_TO_COLOR[chosen]
        
        # Configure this setting.
        trade_hub_data = self.json_interface.get_trade_hub_data(
            guild = ctx.guild,
            ascension = user_account.get_prestige_level(),
            galaxy_x = hub.galaxy_xpos,
            galaxy_y = hub.galaxy_ypos
        )

        trade_hub_data["color_id"] = color_code

        self.json_interface.update_trade_hub_data(
            guild = ctx.guild,
            ascension = user_account.get_prestige_level(),
            galaxy_x = hub.galaxy_xpos,
            galaxy_y = hub.galaxy_ypos,
            new_data = trade_hub_data
        )
        
        await ctx.reply(f"Success, this Trade Hub is now colored {chosen} on the map.")

    
    async def trade_hub_configure(
            self: typing.Self,
            ctx: commands.Context,
            user_account: account.Bread_Account,
            day_seed: str,
            hub_projects: list[dict],
            hub: space.SystemTradeHub,
            actions: tuple[str]
        ) -> None:
        """Configuration for the Trade Hub's upgrades."""
        if len(actions) > 1:
            if actions[1].lower() in ["beacon", "shroud", "shroud_beacon"]:
                await self.trade_hub_configure_beacon(
                    ctx = ctx,
                    user_account = user_account,
                    day_seed = day_seed,
                    hub_projects = hub_projects,
                    hub = hub,
                    actions = actions
                )
                return
            elif actions[1].lower() in ["color", "colour", "colors", "colours"]:
                await self.trade_hub_configure_color(
                    ctx = ctx,
                    user_account = user_account,
                    day_seed = day_seed,
                    hub_projects = hub_projects,
                    hub = hub,
                    actions = actions
                )
                return
        
        available_configuration = ["color"]
        
        if hub.get_upgrade_level(projects.Shroud_Beacon) >= 1:
            available_configuration.append("beacon")
        
        await ctx.reply(f"To configure a specific section of the Trade Hub, use '$bread space hub configure <section> <settings>'\nList of available sections: {', '.join(available_configuration)}")
            
        

    ########################################################################################################################
    #####      BREAD SPACE HUB

    @bread.command(
        name = "hub",
        brief = "Interact with Trade Hubs.",
        description = "Interact with Trade Hubs."
    )
    async def bread_hub(self, ctx,
            *, action: typing.Optional[str] = commands.parameter(description = "The action to perform at the Trade Hub.")
        ):
        await self.space_hub(ctx, action=action)
    
    @space.command(
        name = "hub",
        brief = "Interact with Trade Hubs.",
        description = "Interact with Trade Hubs."
    )
    async def space_hub(self, ctx,
            *, action: typing.Optional[str] = commands.parameter(description = "The action to perform at the Trade Hub.")
        ):
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"I appreciate your interest in Trade Hubs, the nearest access point is in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        if user_account.get_space_level() < 1:
            await ctx.reply("You do not yet have a rocket that can access Trade Hubs. You can purchase a Bread Rocket from the Space Shop.")
            return
        
        galaxy_x, galaxy_y = user_account.get_galaxy_location(json_interface=self.json_interface, correct_center=True)
        
        system = space.get_galaxy_coordinate(
            json_interface = self.json_interface,
            guild = ctx.guild.id,
            galaxy_seed = self.json_interface.get_ascension_seed(user_account.get_prestige_level(), guild=user_account.get("guild_id")),
            ascension = user_account.get_prestige_level(),
            xpos = galaxy_x,
            ypos = galaxy_y,
            load_data = False
        )

        if not system.system:
            await ctx.reply("There is no Trade Hub here, and you are not close enough to a star to create a Trade Hub.")
            return
        
        system_x, system_y = user_account.get_system_location()
        
        system.load_system_data(json_interface=self.json_interface, guild=ctx.guild.id, get_wormholes=False)

        hub = system.trade_hub

        # This logic here is a little crap, but I think it works.
        if hub is None or (hub is not None and hub.get_upgrade_level(projects.Listening_Post) == 0):
            if not (abs(system_x) <= 1 and abs(system_y) <= 1) \
                and not (hub is not None and system_x == hub.system_xpos and system_y == hub.system_ypos):
                await ctx.reply("You are not close enough to a star to create a Trade Hub.")
                return
        
        if action is not None:
            actions = action.split(" ")
            action = actions[0]
            
        day_seed = self.json_interface.get_day_seed(guild=ctx.guild.id)

        hub = system.trade_hub
        
        if system.trade_hub is None:            
            if action == "create":
                if not projects.Trade_Hub.is_affordable_for(
                        day_seed = day_seed,
                        system_tile = hub,
                        user_account=user_account
                    ):
                    await ctx.reply("Sorry, you don't have the resources to create a Trade Hub.")
                    return
                
                print(f"User {ctx.author} creating trade hub in system ({galaxy_x}, {galaxy_y}) on ({system_x}, {system_y})")
                
                projects.Trade_Hub.do_purchase(
                    day_seed = day_seed,
                    system_tile = hub,
                    user_account = user_account
                )

                user_account.increment("trade_hubs_created", 1)

                self.json_interface.set_account(ctx.author, user_account, guild = ctx.guild.id)

                if system_x == 0 and system_y == 0:
                    create_x = random.randint(-1, 1)
                    create_y = random.randint(-1, 1)
                    
                    if create_x == 0 and create_y == 0:
                        if random.randint(1, 2) == 1:
                            create_x += random.randint(0, 1) * 2 - 1
                        else:
                            create_y += random.randint(0, 1) * 2 - 1
                else:
                    create_x = system_x
                    create_y = system_y

                space.create_trade_hub(
                    json_interface = self.json_interface,
                    user_account = user_account,
                    galaxy_x = galaxy_x,
                    galaxy_y = galaxy_y,
                    system_x = create_x,
                    system_y = create_y
                )

                await ctx.reply(f"Well done, you have created a Trade Hub at ({create_x}, {create_y}) in ({galaxy_x}, {galaxy_y})!")
                return

            cost = projects.Trade_Hub.get_price_description(day_seed, hub)
            
            await ctx.reply(f"To create a Trade Hub around this star, you must have the following resources:\n{cost}\n\nOnce you have the resources, use '$bread space hub create' to create the Trade Hub.")
            return
        
        if action == "create":
            await ctx.reply("There is already a Trade Hub in this system.")
            return
        
        if hub.get_upgrade_level(projects.Listening_Post) == 0:
            if not (system_x == system.trade_hub.system_xpos and system_y == system.trade_hub.system_ypos):
                await ctx.reply("You must be on the Trade Hub to use it.")
                return
        
        # Make sure the Trade Hub data exists.
        discovered_trade_hub = False
        
        trade_hub_data = self.json_interface.get_trade_hub_data(
            guild = ctx.guild,
            ascension = user_account.get_prestige_level(),
            galaxy_x = galaxy_x,
            galaxy_y = galaxy_y,
        )

        if len(trade_hub_data) == 0: # i.e. if the trade hub is not currently in the database.
            discovered_trade_hub = True
            space.create_trade_hub(
                json_interface = self.json_interface,
                user_account = user_account,
                galaxy_x = galaxy_x,
                galaxy_y = galaxy_y,
                system_x = system_x,
                system_y = system_y,
                level = hub.trade_hub_level
            )

        
        ##############################################################################################################
        # Can interact with the trade hub!

        hub_projects = space.get_trade_hub_projects(
            json_interface = self.json_interface,
            user_account = user_account,
            system_tile = hub
        )
        
        ##############################################################################################################
        
        if action == "detailed":
            if len(actions) > 1 and actions[1].lower() in ["on", "off", "yes", "no", "y", "n"]:
                if actions[1].lower() in ["on", "yes", "y"]:
                    user_account.set("trade_hub_detailed", True)
                    
                    new_state = True
                else:
                    user_account.set("trade_hub_detailed", False)

                    new_state = False
            else:
                current_state = user_account.get("trade_hub_detailed", True)

                user_account.set("trade_hub_detailed", not current_state)
                new_state = not current_state

            self.json_interface.set_account(ctx.author, user_account, ctx.guild)
            
            if new_state:
                await ctx.reply("Trade Hub messages will now be more detailed.")
            else:
                await ctx.reply("Trade Hub messages will now be less detailed.")
            
            return
            
        ##############################################################################################################

        if action == "contribute":
            await self.trade_hub_contribute(
                ctx = ctx,
                user_account = user_account,
                day_seed = day_seed,
                hub_projects = hub_projects,
                hub = hub,
                actions = actions
            )
            return

        ##############################################################################################################

        if action == "info":
            await self.trade_hub_info(
                ctx = ctx,
                user_account = user_account,
                day_seed = day_seed,
                hub_projects = hub_projects,
                hub = hub,
                actions = actions
            )
            return
        
        ##############################################################################################################

        if action == "level":
            await self.trade_hub_level(
                ctx = ctx,
                user_account = user_account,
                day_seed = day_seed,
                hub_projects = hub_projects,
                hub = hub,
                actions = actions
            )
            return
        
        ##############################################################################################################

        if action == "upgrades" or action == "upgrade":
            await self.trade_hub_upgrades(
                ctx = ctx,
                user_account = user_account,
                day_seed = day_seed,
                hub_projects = hub_projects,
                hub = hub,
                actions = actions
            )
            return
        
        ##############################################################################################################

        if action == "configure" or action == "configuration":
            await self.trade_hub_configure(
                ctx = ctx,
                user_account = user_account,
                day_seed = day_seed,
                hub_projects = hub_projects,
                hub = hub,
                actions = actions
            )
            return

        ##############################################################################################################
        
        detailed = user_account.get("trade_hub_detailed", True) # Default to detailed.

        level_project = projects.Trade_Hub
        max_level = len(level_project.all_costs())

        name = generation.get_trade_hub_name(
            galaxy_seed = self.json_interface.get_ascension_seed(user_account.get_prestige_level(), guild=user_account.get("guild_id")),
            galaxy_x = galaxy_x,
            galaxy_y = galaxy_y
        )

        message_lines = f"**# -- Trade Hub {name} --**"

        if discovered_trade_hub:
            message_lines += "\n*New Trade Hub discovered! Trading using this trade hub is now available.*\n"

        message_lines += f"\nLevel: {hub.trade_hub_level}"
        message_lines += f"\nTrade Hub network range: {hub.trade_distance}"
        message_lines += f"\nCommunication network range: {hub.communication_distance}"
        message_lines += f"\nGalaxy location: ({hub.galaxy_xpos}, {hub.galaxy_ypos})"
        
        if detailed:
            message_lines += f"\nSystem location: ({hub.system_xpos}, {hub.system_ypos})"

        available_upgrades = hub.get_available_upgrades(day_seed)
        if len(available_upgrades) > 0:
            if detailed:
                message_lines += f"\n\nAvailable upgrades:"
                for upgrade in available_upgrades:
                    message_lines += f"\n- {upgrade.name(day_seed, hub)}"
            else:
                if len(available_upgrades) == 1:
                    message_lines += "\n\nThere is 1 available upgrade."
                else:
                    message_lines += f"\n\nThere are {utility.smart_number(len(available_upgrades))} available upgrades."
        
        if len(available_upgrades) > 0 or len(hub.get_purchased_upgrades()) > 0:
            message_lines += f"\nUse '$bread space hub upgrades' to get more information on available and purchased upgrades."

        if hub.trade_hub_level != max_level:
            message_lines += f"\n\nUse '$bread space hub level' to view the progress to level {hub.trade_hub_level + 1}"
        
        ### Projects.
        
        message_lines += "\n\n**# -- Projects --**"

        suffix = "To contribute to a project, use '$bread space hub contribute [project number] [amount] [item]'\nYou can get more information about a project with '$bread space hub info [project number]'"
        
        if detailed:
            suffix += "\n\n*Use '$bread hub detailed off' to enable a more condensed version of this message.*"
        else:
            suffix += "\n\n*Use '$bread hub detailed on' to enable a more detailed version of this message.*"

        for project_id, data in enumerate(hub_projects[:hub.project_count]):
            old = message_lines

            contributions = data.get('contributions')

            message_lines += f"#{project_id + 1}: "
            message_lines += data.get("project").display_info(
                day_seed = day_seed,
                system_tile = hub,
                show_description = detailed,
                compress_description = True,
                completed = data.get("completed", False),
                item_information = contributions
            )
            
            # If detailed is True, this is 2, if it's False, this is 1.
            message_lines += "\n" * (detailed + 1)

            if len(message_lines) >= (1900 - len(suffix)):
                await ctx.reply(old)
                message_lines = f"Continued:\n{message_lines[len(old):]}"
        
        if not detailed:
            message_lines += "\n"
        
        message_lines += suffix

        await ctx.reply(message_lines)







        
    ########################################################################################################################
    #####      BREAD SPACE MOVE

    @bread.command(
        name = "move",
        brief = "Move around in space.",
        description = "Move around in space by commanding the autopilot."
    )
    async def bread_move(self, ctx,
            move_map: typing.Optional[str] = commands.parameter(description = "Which map to move on."),
            move_location: typing.Optional[str] = commands.parameter(description = "The location to move to."),
            confirm: typing.Optional[str] = commands.parameter(description = "Whether to confirm automatically."),
            other: typing.Optional[str] = commands.parameter(description = "Other arguments specific to how you're moving.")
        ):
        await self.space_move(ctx, move_map, move_location, confirm, other)
    
    @space.command(
        name = "move",
        brief = "Move around in space.",
        description = "Move around in space by commanding the autopilot."
    )
    async def space_move(self, ctx,
            move_map: typing.Optional[str] = commands.parameter(description = "Which map to move on."),
            move_location: typing.Optional[str] = commands.parameter(description = "The location to move to."),
            confirm: typing.Optional[str] = commands.parameter(description = "Whether to confirm automatically."),
            other: typing.Optional[str] = commands.parameter(description = "Other arguments specific to how you're moving.")
        ):
        # Check if the player is in the interacting list.
        if ctx.author.id in self.currently_interacting:
            return
        
        # Add the player to the interacting list.
        self.currently_interacting.append(ctx.author.id)


        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Thank you for trying to use the autopilot! The closest autopilot terminal is in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")

            self.remove_from_interacting(ctx.author.id)
            return
        
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        if user_account.get_space_level() < 1:
            await ctx.reply("You do not have access to any rockets with autopilot systems.\nYou can purchase the required rocket from the Space Shop.")

            self.remove_from_interacting(ctx.author.id)
            return
        
        #########################################################

        # Map configuration check.

        if move_map == "map":
            new_state = False

            if move_location in ["on", "off", "yes", "no", "y", "n"]:
                if move_location in ["on", "yes", "y"]:
                    user_account.set("auto_move_map", True)
                    
                    new_state = True
                else:
                    user_account.set("auto_move_map", False)

                    new_state = False
            else:
                current_state = user_account.get("auto_move_map", False)

                user_account.set("auto_move_map", not current_state)
                new_state = not current_state

            self.json_interface.set_account(ctx.author, user_account, ctx.guild)
            
            if new_state:
                await ctx.reply("Automatic map sending after moving has been enabled.")
            else:
                await ctx.reply("Automatic map sending after moving has been disabled.")

            self.remove_from_interacting(ctx.author.id)
            return


        #########################################################

        acceptable_maps = [
            "system", "s",
            "galaxy", "g",
            "wormhole", "w",
            "catapult", "c"
        ]

        if move_map in acceptable_maps:
            if move_map == "s":
                move_map = "system"
            elif move_map == "g":
                move_map = "galaxy"
            elif move_map == "w":
                move_map = "wormhole"
            elif move_map == "c":
                move_map = "catapult"
        elif confirm is None:
            confirm = move_location
            move_location = move_map
            move_map = "system"
        else:
            await ctx.reply("Autopilot error:\nUnrecognized map to move on.")

            self.remove_from_interacting(ctx.author.id)
            return
        
        #########################################################

        confirm_text = ["yes", "y", "confirm"]
        cancel_text = ["no", "n", "cancel"]
            
        ###################################

        autopilot_level = user_account.get(store.Upgraded_Autopilot.name)

        if move_map == "catapult":
            if autopilot_level < 1:
                await ctx.reply(f"Autopilot error:\nGalaxy travel not possible with existing autopilot system.\nAutopilot level: {autopilot_level}, expected 1 or higher.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            hub_tile = user_account.get_system_tile(json_interface=self.json_interface) # type: space.SystemTradeHub

            if hub_tile.type != "trade_hub":
                await ctx.reply("Autopilot error:\nNo Trade Hub found on current tile.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            level = hub_tile.get_upgrade_level(projects.Quantum_Catapult)
            
            if level == 0:
                await ctx.reply("Autopilot error:\nNo catapult found.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            try:
                ending_xpos = parse_int(move_location)
                ending_ypos = parse_int(confirm)
            except ValueError:
                await ctx.reply("Autopilot error:\nNo catapult coordinates provided.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            if ending_xpos == hub_tile.galaxy_xpos and ending_ypos == hub_tile.galaxy_ypos:
                await ctx.reply(f"Autopilot error:\nDistance too short to catapult.")
                self.remove_from_interacting(ctx.author.id)
                return

            distance = math.hypot(ending_xpos - hub_tile.galaxy_xpos, ending_ypos - hub_tile.galaxy_ypos)

            if distance > projects.Quantum_Catapult.max_distance:
                await ctx.reply(f"Autopilot error:\nToo far to launch. Distance: {utility.smart_number(round(distance, 2))}. Maximum distance: {projects.Quantum_Catapult.max_distance}")
                self.remove_from_interacting(ctx.author.id)
                return
            
            galaxy_seed = self.json_interface.get_ascension_seed(
                ascension_id = user_account.get_prestige_level(),
                guild = ctx.guild.id
            )

            ending_coordinate = space.get_galaxy_coordinate(
                json_interface = self.json_interface,
                guild = ctx.guild,
                galaxy_seed = galaxy_seed,
                ascension = user_account.get_prestige_level(),
                xpos = ending_xpos,
                ypos = ending_ypos
            )

            if ending_coordinate.in_nebula and autopilot_level < 2:
                await ctx.reply(f"Autopilot error:\nUnsafe landing point for current autopilot level.\nAutopilot level: {autopilot_level}, 2 or higher is required to land there.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            move_cost = space.get_move_cost_galaxy(
                json_interface = self.json_interface,
                guild = ctx.guild,
                ascension = user_account.get_prestige_level(),
                start_position = (hub_tile.galaxy_xpos, hub_tile.galaxy_ypos),
                end_position = (ending_xpos, ending_ypos)
            )["cost"]

            move_cost = int(move_cost * user_account.get_engine_efficiency_multiplier())

            hub_multiplier = projects.Quantum_Catapult.cost_multipliers[level]

            move_cost = int(move_cost * hub_multiplier)

            if other not in confirm_text:
                current_fuel = user_account.get(values.fuel.text)
                daily_fuel = user_account.get("daily_fuel")
                
                await ctx.reply(f"You are trying to use the Trade Hub's Quantum Catapult to move to {ending_xpos, ending_ypos} on the galaxy map.\nThis will require **{utility.smart_number(move_cost)}** {values.fuel.text}.\nYou have {utility.smart_number(current_fuel)} {values.fuel.text} and {utility.smart_number(daily_fuel)} {values.daily_fuel.text}.\nAre you sure you want to move? Yes or No.")
            
                def check(m: discord.Message):
                    return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id 

                try:
                    msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
                except asyncio.TimeoutError: 
                    await ctx.reply(f"Autopilot error:\nConfirmation timeout, aborting.")
                    self.remove_from_interacting(ctx.author.id)
                    return
                
                if msg.content.lower() in cancel_text:
                    await ctx.reply("Autopilot error:\nCancelled.")

                    self.remove_from_interacting(ctx.author.id)
                    return
                elif msg.content.lower() not in confirm_text:
                    await ctx.reply("Autopilot error:\nUnrecognized confirmation response, aborting.")

                    self.remove_from_interacting(ctx.author.id)
                    return
        
            fuel_item = user_account.get(values.fuel.text)
            daily_fuel = user_account.get("daily_fuel")
            player_fuel = fuel_item + daily_fuel

            if player_fuel < move_cost:
                await ctx.reply("Autopilot error:\nLacking required fuel, aborting.")

                self.remove_from_interacting(ctx.author.id)
                return
            
            # Remove the fuel.
            # Daily fuel is prioritized over regular fuel.
            if move_cost > daily_fuel:
                user_account.set("daily_fuel", 0)
                user_account.increment(values.fuel.text, -(move_cost - daily_fuel))
            else:
                user_account.increment("daily_fuel", -move_cost)
            
            user_account.set("galaxy_xpos", ending_xpos)
            user_account.set("galaxy_ypos", ending_ypos)
            user_account.set("system_xpos", 0)
            user_account.set("system_ypos", 0)
            user_account.increment("galaxy_move_count", 1)

            # Save the player account.
            self.json_interface.set_account(ctx.author.id, user_account, guild = ctx.guild.id)

            item_left = user_account.get(values.fuel.text)
            daily_fuel = user_account.get("daily_fuel")

            message_content = f"Autopilot success:\nSucessfully used the catapult to move to {ending_xpos, ending_ypos} on the galaxy map.\n\nYou have **{utility.smart_number(item_left)} {values.fuel.text}** and **{utility.smart_number(daily_fuel)} {values.daily_fuel.text}** remaining."
            
            auto_map = user_account.get("auto_move_map", False)

            if auto_map:
                try:
                    await self.handle_map(
                        ctx = ctx,
                        map_type = "galaxy",
                        user_account = user_account,
                        content = message_content,
                        reduced_info = True
                    )
                except Exception as e:
                    await ctx.reply(message_content + "\n\n*Map generation failed.*")
                    self.remove_from_interacting(ctx.author.id)
                    
                    # This is kind of a weird situation.
                    # It's sending a message and removing the person from the interacting list,
                    # but then reraising the exception so it will be sent in machine-configure.
                    raise e
            else:
                await ctx.reply(message_content)

            self.remove_from_interacting(ctx.author.id)
            return

            


        if move_map == "wormhole":
            if autopilot_level < 3:
                await ctx.reply(f"Autopilot error:\nWormhole travel not possible with existing autopilot system.\nAutopilot level: {autopilot_level}, expected 3 or higher.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            # Wormhole travel :o
            system_tile = user_account.get_system_tile(json_interface=self.json_interface) # type: typing.Union[space.SystemWormhole, space.SystemTile]

            if system_tile.type != "wormhole":
                await ctx.reply("Autopilot error:\nNo wormhole found.")

                self.remove_from_interacting(ctx.author.id)
                return
            
            move_cost = int(space.MOVE_FUEL_WORMHOLE * user_account.get_engine_efficiency_multiplier())
            
            if move_location not in confirm_text:
                current_fuel = user_account.get(values.fuel.text)
                daily_fuel = user_account.get("daily_fuel")
                
                await ctx.reply(f"You are trying to travel through the wormhole.\nThis will require **{utility.smart_number(move_cost)}** {values.fuel.text}.\nYou have {utility.smart_number(current_fuel)} {values.fuel.text} and {utility.smart_number(daily_fuel)} {values.daily_fuel.text}.\nAre you sure you want to move? Yes or No.")
            
                def check(m: discord.Message):
                    return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id 

                try:
                    msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
                except asyncio.TimeoutError: 
                    await ctx.reply(f"Autopilot error:\nConfirmation timeout, aborting.")
                    self.remove_from_interacting(ctx.author.id)
                    return
                
                if msg.content.lower() in cancel_text:
                    await ctx.reply("Autopilot error:\nCancelled.")

                    self.remove_from_interacting(ctx.author.id)
                    return
                elif msg.content.lower() not in confirm_text:
                    await ctx.reply("Autopilot error:\nUnrecognized confirmation response, aborting.")

                    self.remove_from_interacting(ctx.author.id)
                    return
        
            fuel_item = user_account.get(values.fuel.text)
            daily_fuel = user_account.get("daily_fuel")
            player_fuel = fuel_item + daily_fuel

            if player_fuel < move_cost:
                await ctx.reply("Autopilot error:\nLacking required fuel, aborting.")

                self.remove_from_interacting(ctx.author.id)
                return
            
            end_galaxy_location = system_tile.wormhole_link_location

            pair_tile = system_tile.get_pair()

            end_system_location = (pair_tile.system_xpos, pair_tile.system_ypos)

            # Remove the fuel.
            # Daily fuel is prioritized over regular fuel.
            if move_cost > daily_fuel:
                user_account.set("daily_fuel", 0)
                user_account.increment(values.fuel.text, -(move_cost - daily_fuel))
            else:
                user_account.increment("daily_fuel", -move_cost)


            # Update the player's galaxy location.
            user_account.set("galaxy_xpos", end_galaxy_location[0])
            user_account.set("galaxy_ypos", end_galaxy_location[1])

            # Update the player's system location.
            user_account.set("system_xpos", end_system_location[0])
            user_account.set("system_ypos", end_system_location[1])

            # Save the player account.
            self.json_interface.set_account(ctx.author.id, user_account, guild = ctx.guild.id)

            item_left = user_account.get(values.fuel.text)
            daily_fuel = user_account.get("daily_fuel")

            message_content = f"Autopilot success:\nSucessfully travelled through the wormhole.\n\nYou have **{utility.smart_number(item_left)} {values.fuel.text}** and **{utility.smart_number(daily_fuel)} {values.daily_fuel.text}** remaining."
            
            auto_map = user_account.get("auto_move_map", False)

            if auto_map:
                try:
                    await self.handle_map(
                        ctx = ctx,
                        map_type = "system", # This is a weird scenario since wormholes move on both maps.
                        user_account = user_account,
                        content = message_content,
                        reduced_info = True
                    )
                except Exception as e:
                    await ctx.reply(message_content + "\n\n*Map generation failed.*")
                    self.remove_from_interacting(ctx.author.id)
                    
                    # This is kind of a weird situation.
                    # It's sending a message and removing the person from the interacting list,
                    # but then reraising the exception so it will be sent in machine-configure.
                    raise e
            else:
                await ctx.reply(message_content)

            self.remove_from_interacting(ctx.author.id)
            return
            
        ###################################
        
        HELP_MSG = "Autopilot error:\nUnrecoginized location. Locations should be in the format of '[letter][number]'. A guide can be found on the system and galaxy maps."
        
        if move_location is None:
            await ctx.reply(HELP_MSG)

            self.remove_from_interacting(ctx.author.id)
            return
        
        if len(move_location) > 3:
            await ctx.reply(HELP_MSG)

            self.remove_from_interacting(ctx.author.id)
            return

        telescope_level = user_account.get("telescope_level")
        radius = telescope_level + 2
        diameter = radius * 2 + 1

        letters = "abcdefghijklmnopqrstuvwxyz"

        pattern = "([a-{letter_end}])([{number_start}-{number_end}]{{1,{times}}})".format(
            letter_end = letters[diameter - 1],
            number_start = 1 if diameter < 10 else 0,
            number_end = min(diameter, 9),
            times = len(str(diameter))
        )

        matched = re.match(pattern, move_location.lower())

        if matched is None:
            await ctx.reply(HELP_MSG)

            self.remove_from_interacting(ctx.author.id)
            return
        
        x_modifier = letters.index(matched.group(1).lower()) # group 1 is the letter.
        y_modifier = int(matched.group(2).lower()) - 1 # group 2 is the number.

        if round(math.hypot(abs(x_modifier - radius), abs(y_modifier - radius))) > radius:
            await ctx.reply("Autopilot error:\nUnrecognized location.")

            self.remove_from_interacting(ctx.author.id)
            return
        
        #########################################################
        
        galaxy_seed = self.json_interface.get_ascension_seed(
            ascension_id = user_account.get_prestige_level(),
            guild = ctx.guild.id
        )

        if move_map == "system":
            start_location = user_account.get_system_location()

            # Check if the galaxy tile the player is on is actually a system.
            # If it is, great! If it isn't, the player shouldn't be moving on the system map.
            galaxy_location = user_account.get_galaxy_location(json_interface=self.json_interface)

            current_data = space.get_galaxy_coordinate(
                json_interface = self.json_interface,
                guild = ctx.guild,
                galaxy_seed = galaxy_seed,
                ascension = user_account.get_prestige_level(),
                xpos = galaxy_location[0],
                ypos = galaxy_location[1],
                load_data = True
            )

            # if not current_data.get("system", False):
            if not current_data.system:
                await ctx.reply("Autopilot error:\nNo matter found in current system location, cannot move.")

                self.remove_from_interacting(ctx.author.id)
                return
        
            end_location = (
                start_location[0] + x_modifier - radius,
                start_location[1] + y_modifier - radius
            )

            if math.hypot(*end_location) >= current_data.system_radius + 2:
                await ctx.reply("Autopilot error:\nProvided location outside of system bounds.")

                self.remove_from_interacting(ctx.author.id)
                return
            
            # In the end, determine how much fuel it'll cost to make the move.
            cost_data = space.get_move_cost_system(
                start_position = start_location,
                end_position = end_location
            )

            move_cost = int(cost_data.get("cost", 500) * user_account.get_engine_efficiency_multiplier() * space.get_hyperlane_registrar_bonus(self.json_interface, user_account))
        else:
            if autopilot_level < 1:
                await ctx.reply(f"Autopilot error:\nGalaxy travel not possible with existing autopilot system.\nAutopilot level: {autopilot_level}, expected 1 or higher.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            start_location = user_account.get_galaxy_location(json_interface=self.json_interface)
        
            end_location = (
                start_location[0] + x_modifier - radius,
                start_location[1] + y_modifier - radius
            )

            cost_data = space.get_move_cost_galaxy(
                json_interface = self.json_interface,
                guild = ctx.guild,
                ascension = user_account.get_prestige_level(),
                start_position = start_location,
                end_position = end_location
            )

            # If we're moving between parts of the 2x2 system, the cost is 0 as we're not actually being moved..
            if (end_location in space.ALL_CENTER) and start_location in space.ALL_CENTER:
                cost_data["cost"] = 0
            if start_location in space.ALL_CENTER and any(point in cost_data["points"] for point in space.ALL_CENTER):
                cost_data["cost"] -= space.MOVE_FUEL_GALAXY

            if autopilot_level < 2 and cost_data.get("nebula", False):
                await ctx.reply(f"Autopilot error:\nNebula travel not possible with existing autopilot system.\nAutopilot level: {autopilot_level}, expected 2 or higher.")
                self.remove_from_interacting(ctx.author.id)
                return

            move_cost = int(cost_data.get("cost", 500) * user_account.get_engine_efficiency_multiplier() * space.get_hyperlane_registrar_bonus(self.json_interface, user_account))

        if confirm not in confirm_text:
            current_fuel = user_account.get(values.fuel.text)
            daily_fuel = user_account.get("daily_fuel")

            await ctx.reply(f"You are trying to move from {start_location} to {end_location}.\nThis will require **{utility.smart_number(move_cost)}** {values.fuel.text}.\nYou have {utility.smart_number(current_fuel)} {values.fuel.text} and {utility.smart_number(daily_fuel)} {values.daily_fuel.text}.\nAre you sure you want to move? Yes or No.")
            
            def check(m: discord.Message):
                return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id 
        

            try:
                msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
            except asyncio.TimeoutError: 
                await ctx.reply(f"Autopilot error:\nConfirmation timeout, aborting.")
                self.remove_from_interacting(ctx.author.id)
                return
            
            if msg.content.lower() in cancel_text:
                await ctx.reply("Autopilot error:\nCancelled.")

                self.remove_from_interacting(ctx.author.id)
                return
            elif msg.content.lower() not in confirm_text:
                await ctx.reply("Autopilot error:\nUnrecognized confirmation response, aborting.")

                self.remove_from_interacting(ctx.author.id)
                return
        
        fuel_item = user_account.get(values.fuel.text)
        daily_fuel = user_account.get("daily_fuel")
        player_fuel = fuel_item + daily_fuel

        if player_fuel < move_cost:
            await ctx.reply("Autopilot error:\nLacking required fuel, aborting.")

            self.remove_from_interacting(ctx.author.id)
            return
        
        # Remove the fuel.
        # Daily fuel is prioritized over regular fuel.
        if move_cost > daily_fuel:
            user_account.set("daily_fuel", 0)
            user_account.increment(values.fuel.text, -(move_cost - daily_fuel))
        else:
            user_account.increment("daily_fuel", -move_cost)

        if move_map == "system":
            x_key = "system_xpos"
            y_key = "system_ypos"
        else:
            x_key = "galaxy_xpos"
            y_key = "galaxy_ypos"

            # Increment galaxy_move_count so get_galaxy_location knows to use galaxy_xpos and galaxy_ypos instead of the spawn location.
            user_account.increment("galaxy_move_count", 1)

            # Time to figure out what to set the system position to.
            # This is based on the angle the player is moving at.
            # However, if the target location isn't a system then we can just set it to (0, 0)
            end_data = space.get_galaxy_coordinate(
                json_interface = self.json_interface,
                guild = ctx.guild,
                galaxy_seed = galaxy_seed,
                ascension = user_account.get_prestige_level(),
                xpos = end_location[0],
                ypos = end_location[1],
                load_data = True
            )

            if not end_data.system:
                # If the end location is not a system, then set the system x and y to 0.
                user_account.set("system_xpos", 0)
                user_account.set("system_ypos", 0)
            elif end_location != start_location: # If the galaxy location is the same don't modify the system position.
                # If we're moving between parts of the 2x2 system, do nothing.
                if not ((end_location in space.ALL_CENTER) and start_location in space.ALL_CENTER):
                    # If the location is a system, then determine the size of the system and the angle of attack.
                    x_diff = end_location[0] - start_location[0]
                    y_diff = end_location[1] - start_location[1]

                    if x_diff == 0:
                        if y_diff < 0:
                            angle = math.pi / 2
                        else:
                            angle = math.pi * 1.5
                    else:
                        angle = math.atan(y_diff / x_diff)

                        if x_diff > 0:
                            angle -= math.pi
                    
                    system_radius = end_data.system_radius

                    out_x = int(math.cos(angle) * system_radius)
                    out_y = int(math.sin(angle) * system_radius)

                    user_account.set("system_xpos", out_x)
                    user_account.set("system_ypos", out_y)



        # Update the player's location.
        user_account.set(x_key, end_location[0])
        user_account.set(y_key, end_location[1])

        # Save the player account.
        self.json_interface.set_account(ctx.author.id, user_account, guild = ctx.guild.id)

        item_left = user_account.get(values.fuel.text)
        daily_fuel = user_account.get("daily_fuel")

        message_content = f"Autopilot success:\nSuccessfully moved to {end_location} on the {move_map} map, using {utility.smart_number(move_cost)} {values.fuel.text}.\n\nYou have **{utility.smart_number(item_left)} {values.fuel.text}** and **{utility.smart_number(daily_fuel)} {values.daily_fuel.text}** remaining."

        auto_map = user_account.get("auto_move_map", False)

        if auto_map:
            try:
                await self.handle_map(
                    ctx = ctx,
                    map_type = move_map,
                    user_account = user_account,
                    content = message_content,
                    reduced_info = True
                )
            except Exception as e:
                await ctx.reply(message_content + "\n\n*Map generation failed.*")
                self.remove_from_interacting(ctx.author.id)
                
                # This is kind of a weird situation.
                # It's sending a message and removing the person from the interacting list,
                # but then reraising the exception so it will be sent in machine-configure.
                raise e
        else:
            await ctx.reply(message_content)

        self.remove_from_interacting(ctx.author.id)
        




        

    
        
    ########################################################################################################################
    #####      EPHEMERAL UTILITY
    
    def get_active_ephemeral_list(
            self: typing.Self,
            user_account: account.Bread_Account
        ) -> str:
        """Generates the text for a player's active ephemeral upgrades, to be put in a message.

        Args:
            user_account (account.Bread_Account): The player to generate the text for.

        Returns:
            str: The generated text.
        """    
        active_ephemerals = user_account.get_ephemeral_file()
        active_ephemerals = filter(user_account.get_ephemeral_upgrade, active_ephemerals)
        active_ephemerals = list(map(lambda h: "**" + store.find_ephemeral_upgrade(h).display_name + "**", active_ephemerals))
        
        return (f"You currently have the {utility.list_items(active_ephemerals)} Ephemeral Upgrade{'s' if len(active_ephemerals) != 1 else ''} active." if active_ephemerals else "You do not have an active Ephemeral Upgrade.")
            
    ########################################################################################################################
    #####      BREAD SALVAGE    

    @bread.group(
        name="salvage", 
        help="Salvage your items in a salvage machine.",
        brief="Salvage your items in a salvage machine.",
        invoke_without_command = True,
        pass_context = True
    )
    async def salvage(self, ctx,
            item: typing.Optional[str] = commands.parameter(description = "The item to salvage.")
        ):
        if ctx.invoked_subcommand is not None:
            # If a subcommand was invoked, do nothing.
            return

        # first we make sure this is a valid channel
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Hello! Thanks for trying to salvage your items. The nearest Salvage Machine access port is in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        if user_account.get_space_level() < 1:
            await ctx.reply("You do not yet have a rocket that can access Trade Hubs. You can purchase a Bread Rocket from the Space Shop.")
            return
        
        if not user_account.can_use_salvage():
            await ctx.reply("You are not currently on a Trade Hub with the Salvage Works upgrade.")
            return
        
        # The player can use the salvage machine.
        
        item = values.get_emote(item)
        
        system_tile = user_account.get_system_tile(self.json_interface)
        salvage_level = system_tile.get_upgrade_level(projects.Salvage_Works)
        salvage_addition = (salvage_level - 1) * 5
        
        if item is None:
            active_catalyst = store.find_catalyst(user_account.get("active_catalyst"))
            remaining = max(user_account.get("salvage_remaining") + salvage_addition, 0)
            # remaining = user_account.write_count('salvage_remaining', '**more time')
            
            
            lines = [
                "Welcome to the Salvage Machine!",
                "Here you are able to salvage your items into other items.",
                "Use \"$bread salvage [item]\" to salvage that item.",
                "",
                f"You can salvage items **{utility.write_count(remaining, '**more time')} today.", # The formatting here is a little odd, but it's because write_count adds a space after the number automatically.
                f"You currently have the **{active_catalyst.display_name}** catalyst active for another **{utility.write_count(user_account.get('catalyst_remaining'), 'salvage')}**." if active_catalyst is not None else "You currently do not have a catalyst active.",
                self.get_active_ephemeral_list(user_account),
                "",
                "To view the Salvage Shop, use \"$bread salvage shop\"",
                "To look at the Ephemeral Shop, use \"$bread salvage ephemeral\"",
                "To see what catalysts you can make, use \"$bread salvage catalyst\""
            ]
            await ctx.reply("\n".join(lines))
            return
        
        # Check if the player is in the interacting list.
        if ctx.author.id in self.currently_interacting:
            return
        
        # Add the player to the interacting list.
        self.currently_interacting.append(ctx.author.id)
        
        # Time to actually run the salvage machine.
        print(f"{ctx.author} is requesting to salvage {item}, they have {user_account.get(item.text)} of it.")
        
        if item not in gamble.salvage_options:
            await ctx.reply("It doesn't seem like the Salvage Machine will accept that item.")

            self.remove_from_interacting(ctx.author.id)
            return
        
        if user_account.get(item.text) <= 0:
            await ctx.reply("You don't have enough of that item to salvage.")

            self.remove_from_interacting(ctx.author.id)
            return
        
        if user_account.get("salvage_remaining") + salvage_addition <= 0:
            await ctx.reply(f"Sorry, you can only salvage {salvage_level * 5} times today.")

            self.remove_from_interacting(ctx.author.id)
            return

        user_account.increment("salvage_remaining", -1)
        user_account.increment("lifetime_salvages", 1)
        
        self.json_interface.set_account(ctx.author, user_account, ctx.guild.id)
        
        try:
            active_catalyst = user_account.get_active_catalyst().name
        except:
            active_catalyst = None
            
        if active_catalyst == store.Hydra.name and random.randint(1, 4) == 1:
            # Double time.
            
            game_1 = gamble.LasersGame(
                wager = item,
                json_interface = self.json_interface,
                ctx = ctx
            )
            game_2 = gamble.LasersGame(
                wager = item,
                json_interface = self.json_interface,
                ctx = ctx
            )
            game_1.run_finish = False
            game_2.run_finish = False
            
            # This is an error handling mess, but that's because
            # if either game fails the other one needs to continue.
            
            try:
                await game_1.setup()
            except:
                game_1.run_finish = True
                await game_1.finish()
                
            await asyncio.sleep(1)
            
            try:
                await game_2.setup()
            except:
                game_2.run_finish = True
                await game_2.finish()
            
            # Account for the fact that when Hydra activates it shouldn't consume 2 wager items.
            user_account = self.json_interface.get_account(ctx.author.id, ctx.guild.id) # type: account.Bread_Account
            user_account.increment(item, 1)
            self.json_interface.set_account(ctx.author.id, user_account, ctx.guild.id)
                    
            await asyncio.sleep(2)
            
            tick = 0
            
            while game_1.in_progress or game_2.in_progress:
                options = [g for g in (game_1, game_2) if g.in_progress]
                
                chosen = options[tick % len(options)]
                
                try:
                    await chosen.run_tick()
                except:
                    chosen.run_finish = True
                    await chosen.finish()
                
                await asyncio.sleep(1.5)
                
                tick += 1
            
            if not game_1.run_finish:
                await game_1.finish()
                
                if not game_2.run_finish:
                    await asyncio.sleep(2)
                
            if not game_2.run_finish:
                await game_2.finish()

            self.remove_from_interacting(ctx.author.id)
        else:
            game = gamble.LasersGame(
                wager = item,
                json_interface = self.json_interface,
                ctx = ctx
            )
        
            try:
                await game.setup()
                    
                await asyncio.sleep(2)
            
                while game.in_progress:
                    await game.run_tick()
                    
                    await asyncio.sleep(1.5)
            finally:
                # Even if the game fails, at least run the `.finish()` method.
                await game.finish()
                
                if active_catalyst == store.Sagitta.name and random.randint(1, 2) == 1:
                    # Wait! It isn't dead! Salvage suprise!
                    # There's another ahead, and items likewise
                    # But you can do `$bread space stats`
                    
                    item = game.winning_item
                    
                    # This is kind of a weird way of keeping the won item in limbo.
                    user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
                    user_account.increment(item.text, -1)
                    self.json_interface.set_account(ctx.author, user_account, ctx.guild.id)
                    
                    await asyncio.sleep(2)
                    
                    message = "The Salvage Machine appears to be running again, with the output from the previous salvage as the input!\nMust be that catalyst you're using..."
                    
                    if random.randint(1, 100) == 1:
                        message += "\n\nOr, in other words. Wait! It isn't dead! Salvage suprise!"
                    
                    await ctx.reply(message)
                    
                    await asyncio.sleep(2)
                    
                    user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
                    user_account.increment(item.text, 1)
                    self.json_interface.set_account(ctx.author, user_account, ctx.guild.id)
                    
                    game = gamble.LasersGame(
                        wager = item,
                        json_interface = self.json_interface,
                        ctx = ctx
                    )
                
                    try:
                        await game.setup()

                        await asyncio.sleep(2)
                    
                        while game.in_progress:
                            await game.run_tick()
                            
                            await asyncio.sleep(1.5)
                    finally:
                        # Even if the game fails, at least run the `.finish()` method.
                        await game.finish()

                self.remove_from_interacting(ctx.author.id)
            
        if user_account.get("catalyst_remaining") > 0:
            user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
            
            user_account.increment("catalyst_remaining", -1)
            
            if user_account.get("catalyst_remaining") == 0:
                user_account.set("active_catalyst", None)
            
            self.json_interface.set_account(ctx.author, user_account, ctx.guild.id)
                






        
        
        
    ########################################################################################################################
    #####      BREAD SALVAGE SHOP

    @bread.command(
        name = "salvage_shop",
        brief = "The Salvage Shop.",
        description = "Shortcut to '$bread salvage shop'.",
        aliases = ["salvage_store"],
        hidden = True
    )
    async def salvage_shop_shortcut(self, ctx):
        await ctx.invoke(self.salvage_shop)

    @salvage.command(
        name = "shop",
        brief = "The Salvage Shop.",
        aliases = ["store"]
    )
    async def salvage_shop(self, ctx):

        # first we make sure this is a valid channel
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Hello! Thanks for trying to access the Salvage Shop. The nearest Salvage Machine access port is in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        # we get the account of the user who called it
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        # Make sure the player is able to interact with the shop.
        if not user_account.can_use_salvage():
            await ctx.reply("The entrace to this shop appears to require a Trade Hub that has a Salvage Machine.")
            return
        
        await self.shop_helper(
            ctx = ctx,
            user_account = user_account,
            buyable_list = store.all_salvage_shop_items,
            shop_name = "Salvage Shop"
        )






        
        
        
    ########################################################################################################################
    #####      BREAD EPHEMERAL SHOP

    @bread.group(
        name = "ephemeral",
        brief = "The Ephemeral Shop.",
        description = "Shortcut to '$bread salvage ephemeral'.",
        aliases = ["ephemeral_shop", "ephemeral_store"],
        hidden = True,
        pass_context = True,
        invoke_without_command = True
    )
    async def ephemeral_shop_shortcut(self, ctx):
        if ctx.invoked_subcommand is not None:
            return
        
        await ctx.invoke(self.ephemeral_shop)
    
    @ephemeral_shop_shortcut.command(
        name = "cancel",
        brief = "Cancels an ephemeral upgrade.",
        description = "Cancels an ephemeral upgrade.",
        aliases = ["remove", "clear"]
    )
    async def ephemeral_cancel_shortcut(self, ctx,
            upgrade: typing.Optional[str] = commands.parameter(description = "The name of the upgrade to cancel."),
            confirmation: typing.Optional[str] = commands.parameter(description = "Whether to skip the confirmation.")
        ):
        await ctx.invoke(self.ephemeral_cancel, upgrade=upgrade, confirmation=confirmation)

    @salvage.group(
        name = "ephemeral",
        brief = "The Ephemeral Shop.",
        aliases = ["ephemeral_shop", "ephemeral_store"],
        pass_context = True,
        invoke_without_command = True
    )
    async def ephemeral_shop(self, ctx):
        if ctx.invoked_subcommand is not None:
            return

        # first we make sure this is a valid channel
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Hello! Thanks for trying to access the Ephemeral Shop. The nearest Salvage Machine access port is in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        # we get the account of the user who called it
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        # Make sure the player is able to interact with the shop.
        if not user_account.can_use_salvage():
            await ctx.reply("The entrace to this shop appears to require a Trade Hub that has a Salvage Machine.")
            return
        
        max_ephemeral_upgrades = user_account.get(store.Ephemeral_Light_Beam.name) + 1
        
        await self.shop_helper(
            ctx = ctx,
            user_account = user_account,
            buyable_list = store.all_ephemeral_upgrades,
            shop_name = "Ephemeral Shop",
            prefix = f"You have **{utility.smart_number(user_account.get(values.ephemeral_token.text))} {values.ephemeral_token.text}**." \
                + ("\nAll upgrades in this shop will last until another one is purchased, or when you ascend.\n" if max_ephemeral_upgrades == 1 else f"\nAll upgrades in this shop will last until {max_ephemeral_upgrades} are purchased after it, or when you ascend.\n") \
                + self.get_active_ephemeral_list(user_account),
            suffix = "You can use '$bread salvage ephemeral cancel [upgrade name]' to cancel an upgrade you already have.",
            suffix_line_break = False
        )
    
    @ephemeral_shop.command(
        name = "cancel",
        brief = "Cancels an ephemeral upgrade.",
        description = "Cancels an ephemeral upgrade.",
        aliases = ["remove", "clear"]
    )
    async def ephemeral_cancel(self, ctx,
            upgrade: typing.Optional[str] = commands.parameter(description = "The name of the upgrade to cancel."),
            confirmation: typing.Optional[str] = commands.parameter(description = "Whether to skip the confirmation.")
        ):

        # first we make sure this is a valid channel
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Hello! Thanks for trying to cancel your Ephemeral Upgrade, the nearest cancel terminal is over in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        if upgrade is None:
            await ctx.reply("Please provide the name of the upgrade you want to cancel.")
            return
        
        if confirmation is None:
            confirmation = ""
        
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)
        upgrade_file = user_account.get_ephemeral_file()
        
        if not upgrade_file: # If the list is empty.
            await ctx.reply("You do not have any Ephemeral Upgrades.")
            return
        
        found_upgrade = store.find_ephemeral_upgrade(upgrade)
        
        if not found_upgrade:
            await ctx.reply("I don't recognize that Ephemeral Upgrade.")
            return
        
        if found_upgrade.name not in upgrade_file:
            await ctx.reply("You don't currently have that upgrade.")
            return
                
        confirm_text = ["yes", "y", "confirm"]
        cancel_text = ["no", "n", "cancel"]
        
        if confirmation.lower() in cancel_text:
            await ctx.reply("You are planning to c- No? Uh, okay, I guess.")
            return
        elif confirmation.lower() not in confirm_text:
            if ctx.author.id in self.currently_interacting:
                return
            
            # If it gets here we need to prompt the user to make sure they
            # want to overwrite their existing catalyst with the new one.
            
            def check(m: discord.Message):  # m = discord.Message.
                return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
            
            await ctx.reply(f"You are planning to cancel the **{found_upgrade.display_name}** Ephemeral Upgrade." \
                            + "\nThis action is irreversable, so if you would like to have it again you will need to purchase it again." \
                            + f"\nAre you sure you want to proceed? Yes or no.")
            
            self.currently_interacting.append(ctx.author.id)
            
            try:
                msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
            except asyncio.TimeoutError: 
                await ctx.reply("I'm sorry, but you have taken too long, please start over.")
                self.remove_from_interacting(ctx.author.id)
                return

            if msg.content.lower() in cancel_text:
                await ctx.reply("Very well, come back later if you would like to cancel an Ephemeral Upgrade.")

                self.remove_from_interacting(ctx.author.id)
                return
            elif msg.content.lower() not in confirm_text:
                await ctx.reply("I'm not entirely sure what that is, please try again.")

                self.remove_from_interacting(ctx.author.id)
                return
            
            self.remove_from_interacting(ctx.author.id)
        
        upgrade_file.remove(found_upgrade.name)
        user_account.set("ephemeral_upgrades", upgrade_file)
        self.json_interface.set_account(ctx.author.id, user_account, ctx.guild.id)
        
        await ctx.reply(f"You have cancelled the **{found_upgrade.display_name}** Ephemeral Upgrade.\nYou can visit the Ephemeral Shop to purchase it again or to purchase another upgrade.")
        
        

        
        






        
        
        
    ########################################################################################################################
    #####      BREAD SALVAGE SHOP

    @bread.command(
        name = "catalyst",
        brief = "Create catalysts.",
        description = "Shortcut to '$bread salvage catalyst'.",
        aliases = ["catalyst_shop", "catalyst_store", "catalysts", "catalysts_shop", "catalysts_store",
                   "enzyme", "enzyme_shop", "enzyme_store", "enzymes", "enzymes_shop", "enzymes_store"],
        hidden = True
    )
    async def catalyst_shop_shortcut(self, ctx):
        await ctx.invoke(self.catalyst_shop)

    @salvage.command(
        name = "catalyst",
        brief = "Create catalysts.",
        aliases = ["catalyst_shop", "catalyst_store", "catalysts", "catalysts_shop", "catalysts_store",
                   "enzyme", "enzyme_shop", "enzyme_store", "enzymes", "enzymes_shop", "enzymes_store"]
    )
    async def catalyst_shop(self, ctx):

        # first we make sure this is a valid channel
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Hello! Thanks for trying to access the Catalyst Shop. The nearest Salvage Machine access port is in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        # we get the account of the user who called it
        user_account = self.json_interface.get_account(ctx.author, guild = ctx.guild.id)

        # Make sure the player is able to interact with the shop.
        if not user_account.can_use_salvage():
            await ctx.reply("The catalyst creation machine appears to be a part of a Salvage Machine within a Trade Hub.")
            return
            
        await self.shop_helper(
            ctx = ctx,
            user_account = user_account,
            buyable_list = store.all_catalysts,
            shop_name = "Catalyst Store",
            prefix = f"Catalysts temporary upgrades that improve the Salvage Machine in some way.\nEach catalyst lasts for **{user_account.get_catalyst_length()}** salvages."
        )
            
            
        




        

    
        
    ########################################################################################################################
    #####      BREAD ANARCHY CHESSATRON    

    @bread.command(
        name="anarchy_chessatron", 
        aliases=["anarchy_tron", "atron"],
        help="Create Anarchy Chessatrons.\n\nAnarchy Chessatrons are affected by auto chessatron, which can be toggled with '$bread chessatron [on/off]'.",
        brief="Create Anarchy Chessatrons."
    )
    async def anarchy_chessatron(self, ctx,
            amount: typing.Optional[parse_int] = commands.parameter(description = "The amount of Anarchy Chessatrons to create.")
        ):
        if get_channel_permission_level(ctx) < PERMISSION_LEVEL_ACTIVITIES:
            await ctx.reply(f"Thank you for your interest in creating anarchy chessatrons! You can do so over in {self.json_interface.get_rolling_channel(ctx.guild.id)}.")
            return
        
        if amount is not None:
            if amount < 0:
                amount = None

            await self.anarchy_chessatron_completion(
                ctx = ctx,
                force = True,
                amount = amount
            )
        else:
            await self.anarchy_chessatron_completion(
                ctx = ctx,
                force = True
            )

        
    ########################################################################################################################
    #####      ANARCHY CHESSATRON COMPLETION
    
    async def anarchy_chessatron_completion(
            self: typing.Self,
            ctx: commands.Context,
            force: bool = False,
            amount = None
        ) -> None:
        """Runs the anarchy chessatron creation animation, as well as making the anarchy chessatrons themselves.

        Args:
            ctx (commands.Context): The context the anarchy chessatron creation was invoked in.
            force (bool, optional): Whether to override `auto_chessatron`. Defaults to False.
            amount (int, optional): The amount of anarchy chessatrons to make. Will make as many as possible if None is provided. Defaults to None.
        """
        user_account = self.json_interface.get_account(ctx.author, guild=ctx.guild.id)

        if user_account.get("auto_chessatron") is False and force is False:
            return
        
        full_chess_set = values.anarchy_pieces_black_biased + values.anarchy_pieces_white_biased

        # pointwise integer division between the full chess set and the set of the user's pieces.
        valid_trons = min([user_account.get(x.text) // full_chess_set.count(x) for x in values.all_anarchy_pieces])

        # iteration ends at the minimum value, make sure amount is never the minimum. 'amount is None' should mean no max ...
        # ... has been specified, so make as many trons as possible.
        if amount is None: 
            amount = valid_trons + 1

        trons_to_make = min(valid_trons, amount)

        # Nothing to do if we're not making any anarchy trons.
        if trons_to_make == 0:
            return
        
        chessatron_value = user_account.get_anarchy_chessatron_dough_amount(include_prestige_boost=False)
        board = board = self.format_anarchy_pieces(user_account.values)

        # Remove the anarchy pieces from the account.
        for anarchy_piece in full_chess_set:
            user_account.increment(anarchy_piece, -trons_to_make)

        

        # first we add the dough and attributes
        total_dough_value = user_account.add_dough_intelligent(chessatron_value * trons_to_make)
        user_account.add_item_attributes(values.anarchy_chessatron, trons_to_make)

        # we save the account
        self.json_interface.set_account(ctx.author, user_account, ctx.guild.id)

        # then we send the tron messages
        if not user_account.get("tron_animation"):
            await ctx.reply(f"Congratuations! You have made {utility.write_count(trons_to_make, 'Anarchy Chessatron')}! For this you have been awarded **{utility.smart_number(total_dough_value)} dough**!\n\n{values.anarchy_chessatron.text} x {utility.smart_number(trons_to_make)}")
            
        elif trons_to_make < 3:
            for _ in range(trons_to_make):
                await ctx.reply(f"You've collected all the anarchy pieces! Congratulations!")
                await asyncio.sleep(1)

                await ctx.reply(board)
                await asyncio.sleep(1)

                await ctx.reply(f"For an incredible feat like this, you have been awarded the Anarchy Chessatron!")
                await asyncio.sleep(1)

                await ctx.reply(values.anarchy_chessatron.text)
                await asyncio.sleep(1)

                await ctx.reply(f"Amazing work! You have also been awarded **{utility.smart_number(total_dough_value//trons_to_make)} dough!**")
                await asyncio.sleep(1)

        elif trons_to_make < 20:
            for _ in range(trons_to_make):
                await ctx.reply(f"Very well done! You have collected all the anarchy pieces!\n\n{board}")
                await asyncio.sleep(1)

                await ctx.reply(f"Not only have you been awarded the prestigious {values.anarchy_chessatron.text}, but you also have been awarded **{utility.smart_number(total_dough_value//trons_to_make)} dough**!")
                await asyncio.sleep(1)

        elif trons_to_make < 5000:
            await ctx.reply(f"You've collected all the anarchy pieces again! Great job! You have enough pieces to make {utility.smart_number(trons_to_make)} Anarchy Chessatrons! Here's your reward of **{utility.smart_number(total_dough_value)} dough**!")
            await asyncio.sleep(1)

            max_per = 1800 // len(values.anarchy_chessatron.text)
            
            full_messages = trons_to_make // max_per
            extra = trons_to_make % max_per
            
            if full_messages >= 1:
                send = values.anarchy_chessatron.text * max_per
                for _ in range(full_messages):
                    await ctx.reply(send)
                    await asyncio.sleep(1)
            
            if extra >= 1:
                await ctx.reply(values.anarchy_chessatron.text * extra)
                await asyncio.sleep(1)


        else:
            await ctx.reply(f"Wow! You have so many anarchy pieces! In fact, you have enough to make a shocking {utility.smart_number(trons_to_make)} Anarchy Chessatrons!")
            await asyncio.sleep(1)

            await ctx.reply(f"Here are your new Anarchy Chessatrons:\n{values.anarchy_chessatron.text} x {utility.smart_number(trons_to_make)}\n\nAnd here is your **{utility.smart_number(total_dough_value)} dough**!")
            await asyncio.sleep(1)

    #############################################################################################################################
    ##########      ADMIN   #################
    #########################################


    @bread.group(
        brief="[Restricted]",
    )
    async def admin(self, ctx):
        if not (await verification.is_admin_check(ctx)):
            await ctx.reply(verification.get_rejection_reason())
            return
        
        if ctx.invoked_subcommand is None:
            print("admin called on nothing")
            return

    async def await_confirmation(
            self: typing.Self,
            ctx: commands.Context,
            force: bool = False,
            message: str = "Are you sure you would like to proceed?"
        ) -> bool:
        """Waits for confirmation, and returns a boolean based on the result."""

        load_dotenv()
        IS_PRODUCTION = getenv('IS_PRODUCTION')
        if force or IS_PRODUCTION == 'True':
            def check(m: discord.Message):  # m = discord.Message.
                return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id 
            await ctx.reply(message+" y/n.")
            try:
                msg = await self.bot.wait_for('message', check = check, timeout = 60.0)
            except asyncio.TimeoutError: 
                # at this point, the check didn't become True, let's handle it.
                await ctx.reply(f"Timed out.")
                return False
            response = msg.content
            if "y" in response.lower():
                await ctx.reply("Proceeding.")
                return True
            elif "n" in response.lower():
                await ctx.reply("Cancelled.")
                return False
            else:
                await ctx.reply("Unknown response, cancelled.")
                return False
        else:
            return True

    ########################################################################################################################
    #####      ADMIN SET

    @admin.command(
        name = "set",
        brief="Sets a value manually.",
        help = "Usage: bread admin set [optional Member] key value [optional 'force']"
    )
    @commands.check(verification.is_admin_check)
    async def set_command(self, ctx,
                    user: typing.Optional[discord.Member], 
                    key: typing.Optional[str],
                    value: typing.Optional[parse_int],
                    do_force: typing.Optional[str]):
        # Ensure arguments are correct.
        output = ""
        if user is None:
            output += "Applying to self\n"
            user = ctx.author
        
        if key is None:
            await ctx.reply("Please provide the key to set.")
            return
        
        if value is None:
            await ctx.reply("Please provide the value to set the key to.")
            return
        
        # Arguments are correct.
        
        if await self.await_confirmation(ctx) is False:
            return
        
        print("Bread Admin Set: User is "+str(user)+", key is '"+str(key)+"', value is "+str(value))
        
        # file = self.json_interface.get_file_for_user(user)
        account = self.json_interface.get_account(user, guild = ctx.guild.id)
        file = account.values

        
        #use values module to grab emote name
        provisional_emote = values.get_emote_text(key)
        if provisional_emote is not None:
            key_name = provisional_emote
        else:
            #use it straight
            key_name = key
        
        if key_name not in file.keys():
            await ctx.send("Key does not exist.")
            if (do_force is not None and do_force.lower() == "force") or (await self.await_confirmation(ctx, True) is True):
                file[key_name] = 0
            else:
                output += "Aborting.\n"
                await ctx.send(output)
                return

        file[key_name] = value
        account.values = file
        self.json_interface.set_account(user, account, guild = ctx.guild.id)
        
        await ctx.send(output+"Done.")

    ########################################################################################################################
    #####      ADMIN INCREMEMNT

    @admin.command(
        brief="Increments a value.",
        help = "Usage: bread admin increment [optional Member] key value [optional 'force']"
    )
    @commands.check(verification.is_admin_check)
    async def increment(self, ctx, 
                    user: typing.Optional[discord.Member], 
                    key: typing.Optional[str],
                    value: typing.Optional[parse_int],
                    do_force: typing.Optional[str]):
        # Ensure the arguments are correct.
        output = ""
        if user is None:
            output += "Applying to self\n"
            user = ctx.author
        
        if key is None:
            await ctx.reply("Please provide the key to increment.")
            return
        
        if value is None:
            await ctx.reply("Please provide the value to increment the key by.")
            return
        
        # Arguments are correct.

        if await self.await_confirmation(ctx) is False:
            return
        print("Bread Admin Increment: User is "+str(user)+", key is '"+str(key)+"', value is "+str(value))
        
        # file = self.json_interface.get_file_for_user(user)
        account = self.json_interface.get_account(user, guild = ctx.guild.id)
        file = account.values

        
        #use values module to grab emote name
        provisional_emote = values.get_emote_text(key)
        if provisional_emote is not None:
            key_name = provisional_emote
        else:
            #use it straight
            key_name = key
        
        if key_name not in file.keys():
            await ctx.send("Key does not exist.")
            if (do_force is not None and do_force.lower() == "force") or (await self.await_confirmation(ctx, True) is True):
                file[key_name] = 0
            else:
                output += "Aborting.\n"
                await ctx.send(output)
                return
                

        file[key_name] = value + file[key_name]

        account.values = file
        self.json_interface.set_account(user, account, guild = ctx.guild.id)

        await ctx.send(output+"Done.")

    ########################################################################################################################
    #####      ADMIN RESET_ACCOUNT

    @admin.command(
        brief="Resets a member's account.",
        help = "Usage: bread admin reset_account [required member]"
    )
    @commands.check(verification.is_admin_check)
    async def reset_account(self, ctx,
            user: typing.Optional[discord.Member]
        ):
        if user is None:
            await ctx.reply("Please provide the member to reset the account of.")
            return
        
        if await self.await_confirmation(ctx) is False:
            return
        user_account = self.json_interface.get_account(user, guild = ctx.guild.id)
        # username = user_account.get("username")
        # display_name = user_account.get("display_name")
        user_account.reset_to_default()
        # user_account.set("username", username)
        # user_account.set("display_name", display_name)
        self.json_interface.set_account(user, user_account, guild = ctx.guild.id)
        print (f"Reset account for {user.display_name}")
        await ctx.send("Done.")

    ########################################################################################################################
    #####      ADMIN COPY_ACCOUNT

    @admin.command(
        brief="Copies one account to another.",
        help = "Usage: bread admin copy_account [source member] [destination member]"
    )
    @commands.check(verification.is_admin_check)
    async def copy_account(self, ctx,
            origin_user: typing.Optional[discord.Member],
            target_user: typing.Optional[discord.Member]
        ):
        if origin_user is None:
            await ctx.reply("Please provide the member to copy the account of.")
            return
        
        if target_user is None:
            await ctx.reply("Please provide the member to paste the account data into.")
            return
        
        if await self.await_confirmation(ctx) is False:
            return
    
        origin_account = self.json_interface.get_account(origin_user, guild = ctx.guild.id)
        
        # hacky copy operation
        target_account = account.Bread_Account.from_dict(str(target_user.id), origin_account.to_dict(), self.json_interface)
        # self.json_interface.set_account(target_user, target_account)
        
        # target_account = self.json_interface.get_account(target_user)
        target_account.values["id"] = target_user.id
        target_account.values["username"] = target_user.name
        #target_account.values["display_name"] = target_user.display_name
        target_account.values["display_name"] =  get_display_name(target_user)

        self.json_interface.set_account(target_user, target_account, guild = ctx.guild.id)

        print (f"Copied account from {origin_user.name} to {target_user.name}")
        await ctx.send("Done.")

    ########################################################################################################################
    #####      ADMIN SERVER_BOOST

    @admin.command(
        brief="Rewards all server boosters.",
        help = "Usage: bread admin reward_all_server_boosters"
    )
    @commands.check(verification.is_admin_check)
    async def reward_all_server_boosters(self, ctx):
        # we will find the dough from a daily roll, and award some multiple of that amount
        # first get all boosters
        boosters = ctx.guild.premium_subscribers
        for booster in boosters:
            await self.reward_single_server_booster(ctx, booster, 1)
            await asyncio.sleep(1)

        await ctx.send("Done.")


    @admin.command(
        brief="Rewards first server boost.",
        help = "Usage: bread admin reward_single_server_booster [member] [optional multiplier, defaults to 1]"
    )
    @commands.check(verification.is_admin_check)
    async def reward_single_server_booster(self, ctx,
            user: typing.Optional[discord.Member],
            multiplier: typing.Optional[float] = 1
        ):
        if user is None:
            await ctx.reply("Please provide the member to reward.")
            return
        
        #first get user account
        user_account = self.json_interface.get_account(user, guild = ctx.guild.id)

        result = rolls.bread_roll(
            roll_luck= user_account.get("loaf_converter")+1, 
            roll_count= user_account.get("max_daily_rolls"),
            user_account=user_account,
            json_interface=self.json_interface
        )

        value = result.get("value")

        portfolio_value = user_account.get_portfolio_value()

        value = round(value + portfolio_value * 0.04) # 4% of portfolio value

        value = round(value * multiplier) # X days worth of rolls

        added_value = user_account.add_dough_intelligent(value)
        self.json_interface.set_account(user, user_account, guild = ctx.guild.id)
        await ctx.send(f"Thank you {user.mention} for boosting the server! {utility.smart_number(added_value)} dough has been deposited into your account.")
        

    
    # I'm not sure why this exists, since it just runs reward_single_server_booster.
    @admin.command(
        brief="Rewards first server boost.",
        help = "Usage: bread admin reward_single_server_booster [member]"
    )
    @commands.check(verification.is_admin_check)
    async def server_boost(self, ctx,
            user: typing.Optional[discord.Member]
        ):
        if user is None:
            await ctx.reply("Please provide the member to reward.")
            return
        
        # this will increase their dough by 5x their max daily rolls
        await self.reward_single_server_booster(ctx, user, 1)
    
    @admin.command(
        brief="Rewards additional server boost.",
        help = "Usage: bread admin server_boost_additional [member]"
    )
    @commands.check(verification.is_admin_check)
    async def server_boost_additional(self, ctx,
            user: typing.Optional[discord.Member]
        ):
        if user is None:
            await ctx.reply("Please provide the member to reward.")
            return
        
        await self.reward_single_server_booster(ctx, user, .5)


    ########################################################################################################################
    #####      ADMIN SHOW

    @admin.command(
        brief="Shows raw values.",
        help = "Usage: bread admin show [optional member]"
    )
    @commands.check(verification.is_admin_check)
    async def show(self, ctx,
            user: typing.Optional[discord.Member]
        ):
        output = ""
        if user is None:
            output += "Applying to self.\n"
            user = ctx.author

        file = self.json_interface.get_file_for_user(user, guild = ctx.guild.id)
        for key in file.keys():
            if key == "display_name":
                if file[key] in ["@everyone", "@here"]:
                    output += "display_name -- (not shown)\n"
                    continue

            output += key + " -- " + str(file[key]) + "\n"
            if len(output) > 1900:
                await ctx.send(output)
                output = ""

        print("Outputting file for "+user.display_name)
        print(str(file))
        await ctx.send(output)

    ########################################################################################################################
    #####      ADMIN SHOW_CUSTOM

    @admin.command(
        brief="Shows a custom file.",
        help = "Usage: bread admin show_custom [file name]\n\nNote that this can reveal hidden info, like space seeds."
    )
    @commands.check(verification.is_admin_check)
    async def show_custom(self, ctx,
            filename: typing.Optional[str]
        ):
        if filename is None:
            await ctx.reply("Please provide the file name.")
            return
        
        data = self.json_interface.get_custom_file(filename, guild = ctx.guild.id)
        file_text = json.dumps(data, indent=4)

        fake_file = io.StringIO(file_text)
        final_file = discord.File(fake_file, filename="export.json")

        await ctx.reply(file=final_file)

    ########################################################################################################################
    #####      ADMIN DUMP_MAP_DATA

    @admin.command(
        brief="Dumps the space map data.",
        help = "Usage: bread admin dump_map_data"
    )
    @commands.check(verification.is_admin_check)
    async def dump_map_data(self, ctx,
            ascension: typing.Optional[int]
        ):
        if ascension is None:
            await ctx.reply("Please provide the ascension to use.")
            return
    
        data = self.json_interface.get_space_map_data(ascension, ctx.guild)
        file_text = json.dumps(data, indent=4)

        fake_file = io.StringIO(file_text)
        final_file = discord.File(fake_file, filename="map_dump.json")

        await ctx.reply(file=final_file)

    ########################################################################################################################
    #####      ADMIN SET_MAX_PRESTIGE

    @admin.command(
        brief="Sets the max prestige level.",
        help = "Usage: bread admin set_max_prestige_level [value]"
    )
    @commands.check(verification.is_admin_check)
    async def set_max_prestige_level(self, ctx,
            value: typing.Optional[parse_int]
        ):
        if value is None:
            await ctx.reply("Please provide the new max prestige level.")
            return
        
        if await self.await_confirmation(ctx) is False:
            return
        prestige_file = self.json_interface.get_custom_file("prestige", guild = ctx.guild.id)
        prestige_file["max_prestige_level"] = value
        self.json_interface.set_custom_file("prestige", prestige_file, guild = ctx.guild.id)
        await ctx.send("Done.")

    ########################################################################################################################
    #####      ADMIN ALLOW / DISALLOW

    @admin.command(
        brief="Allows usage of the bread machine.",
        help = "Usage: bread admin allow [member]"
    )
    @commands.check(verification.is_admin_check)
    async def allow(self, ctx,
            user: typing.Optional[discord.Member]
        ):
        if user is None:
            print("Bread Allow failed to recognize user "+str(user))
            ctx.reply("User reference not resolvable, please retry.")
            return
        user_account = self.json_interface.get_account(user, ctx.guild.id)
        user_account.set("allowed", True)
        self.json_interface.set_account(user, user_account, ctx.guild.id)

        await ctx.send("Done.")
        

    @admin.command(
        brief="Disllows usage of the bread machine.",
        help = "Usage: bread admin disallow [member]"
    )
    @commands.check(verification.is_admin_check)
    async def disallow(self, ctx,
            user: typing.Optional[discord.Member]
        ):
        if user is None:
            print("Bread Disallow failed to recognize user "+str(user))
            ctx.reply("User reference not resolvable, please retry.")
            return
        
        user_account = self.json_interface.get_account(user, ctx.guild.id)
        user_account.set("allowed", False)
        self.json_interface.set_account(user, user_account, ctx.guild.id)

        await ctx.send("Done.")

    ########################################################################################################################
    #####      ADMIN BACKUP


    @admin.command(
        brief="Creates a backup of the database.",
        help = "Usage: bread admin backup"
    )
    @commands.is_owner()
    async def backup(self, ctx):
        print("backing up")
        self.json_interface.create_backup()
        await ctx.send("Done.")

    ########################################################################################################################
    #####      ADMIN DAILY_RESET

    @admin.command(
        brief="Runs the Bread o' Clock daily reset.",
        help = "Usage: bread admin daily_reset"
    )
    @commands.check(verification.is_admin_check)
    async def daily_reset(self, ctx):
        if await self.await_confirmation(ctx) is False:
            return
        # self.reset_internal(ctx.guild.id)
        self.reset_internal()
        await ctx.send("Done.")
        
    def get_highest_lifetime_dough(
            self: typing.Self,
            guild: typing.Union[discord.Guild, str, int]
        ) -> dict[str, int]:
        lifetime_results = {}
        
        all_accounts = self.json_interface.get_all_user_accounts(guild)
        
        for check_account in all_accounts:
            prestige = check_account.get_prestige_level()
            
            account_sum = check_account.get("lifetime_dough") + check_account.get("earned_dough")
            account_sum += check_account.get("gamble_winnings")
            account_sum += self.get_portfolio_combined_value(check_account.user_id, guild)
            
            if str(prestige) not in lifetime_results:
                lifetime_results[str(prestige)] = account_sum
            elif account_sum > lifetime_results[str(prestige)]:
                lifetime_results[str(prestige)] = account_sum
            
        return lifetime_results

    def reset_space_guild(
            self: typing.Self,
            guild: typing.Union[discord.Guild,str,int]
        ) -> None:
        """Twice per day reset for Bread Space."""

        # Set a new day seed.
        space_data = self.json_interface.get_space_data(guild=guild)

        space_data["day_seed"] = space.generate_galaxy_seed()
        
        # For the Stonk Exchange project it needs to have the highest lifetime_dough stat at the start of the tick for each ascension
        space_data["lifetime_highest"] = self.get_highest_lifetime_dough(guild)

        # Reset project contributions.
        blank_projects = {
            "project_1": {},
            "project_2": {},
            "project_3": {},
            "project_4": {},
            "project_5": {}
        }
        for ascension_key, ascension_data in space_data.copy().items():
            if not ascension_key.startswith("ascension"):
                continue

            for trade_hub_key in ascension_data.get("trade_hubs", {}):
                ascension_data["trade_hubs"][trade_hub_key]["project_progress"] = blank_projects.copy()

                if "shroud_beacon_queue" in ascension_data["trade_hubs"][trade_hub_key].get("settings", {}):
                    settings = ascension_data["trade_hubs"][trade_hub_key].get("settings", {})
                    settings["shroud_beacon_setting"] = ascension_data["trade_hubs"][trade_hub_key].get("settings", {}).get("shroud_beacon_queue")
                    settings.pop("shroud_beacon_queue")
            
            space_data[ascension_key] = ascension_data

        self.json_interface.set_custom_file("space", file_data=space_data, guild=guild)
    
    def reset_space_all(self: typing.Self) -> None:
        """Twice per day space reset for all guilds in the JSON interface."""
        print("Bread Space: Running daily reset on all guilds.")

        for guild_id in self.json_interface.get_list_of_all_guilds():
            self.reset_space_guild(guild_id)
        
        print("Bread Space: Done.")

    def reset_internal(
            self: typing.Self,
            guild: typing.Optional[typing.Union[discord.Guild,str,int]] = None
        ) -> None:
        """Runs the daily reset."""

        print("Internal daily reset called")
        self.currently_interacting.clear()

        self.reset_space_all()

        if guild is not None:
            guild_id = get_id_from_guild(guild)

            self.reset_space(guild_id)
            for account in self.json_interface.get_all_user_accounts(guild_id):
                account.daily_reset()
                self.json_interface.set_account(account.get("id"), account, guild_id)
        else: #call for all accounts
            for guild_id in self.json_interface.get_list_of_all_guilds():
                for account in self.json_interface.get_all_user_accounts(guild_id):
                    account.daily_reset()
                    self.json_interface.set_account(account.get("id"), account, guild_id)

        """
        #wipe the accounts cache since we'll be direcly manipulating data. 
        # Would be better to avoid this in the future.
        self.json_interface.accounts.clear()

        #print(f"Daily reset: database is: \n{files}")
        for key in files.keys():
        #for file in files:
            file = files[key]
            #print(f"Individual file is: \n{file}")
            if "daily_rolls" in file.keys():
                file["daily_rolls"] = 0
            if "daily_gambles" in file.keys():
                file["daily_gambles"] = 0
        """

    ########################################################################################################################
    #####      ADMIN PURGE_ACCOUNT_CACHE

    #depreciated, we're avoiding using the account cache now
    @admin.command(
        brief="Clears the now unused account cache.",
        help = "Usage: bread admin purge_account_cache"
    )
    @commands.is_owner()
    async def purge_account_cache(self, ctx):
        self.json_interface.accounts.clear()
        await ctx.send("Done.")

    ########################################################################################################################
    #####      ADMIN RENAME

    # this will take one value from each account and rename it to something different.

    @admin.command(
        brief="Renames global key to something else.",
        help = "Usage: bread admin rename [current key] [new key]"
    )
    @commands.check(verification.is_admin_check)
    async def rename(self, ctx,
            starting_name: typing.Optional[str],
            ending_name: typing.Optional[str]
        ):
        if starting_name is None:
            await ctx.reply("Please provide the current key name.")
            return
        
        if ending_name is None:
            await ctx.reply("Please provide the new key name.")
            return

        all_guilds = self.json_interface.get_list_of_all_guilds()
        for guild_id in all_guilds:
            for account in self.json_interface.get_all_user_accounts(guild_id):
                if starting_name in account.values.keys():
                    account.set(ending_name, account.get(starting_name))
                    del account.values[starting_name]
                    self.json_interface.set_account(account.get("id"), account, guild_id)


        # # we get the guild and then all the members in it
        # guild = ctx.guild
        # all_members = guild.members

        # # we iterate through all the members and rename the key
        # for member in all_members:
        #     # make sure they have an account
        #     if self.json_interface.has_account(member):
        #         # get the account
        #         account = self.json_interface.get_account(member)

        #         # rename the key
        #         if starting_name in account.values.keys():
        #             account.values[ending_name] = account.values[starting_name]
        #             del account.values[starting_name]

        #         # save the account
        #         self.json_interface.set_account(member, account)

        # save the database      
        self.json_interface.internal_save()


        await ctx.send("Done.")


    ########################################################################################################################
    #####      ADMIN GOD_ACCOUNT

    @admin.command(
        brief="Sets a member's stats to harcoded values.",
        help = "Usage: bread admin god_account [optional member]"
    )
    @commands.check(verification.is_admin_check)
    async def god_account(self, ctx,
            user: typing.Optional[discord.Member]
        ):

        if await self.await_confirmation(ctx) is False:
            return

        if user is None:
            user = ctx.author
        
        account = self.json_interface.get_account(user, guild = ctx.guild.id)

        account.reset_to_default()

        account.set("total_dough", 10000000000000000000000000000)
        account.set("loaf_converter", 128)
        account.set("max_daily_rolls", 1400)
        account.set("auto_chessatron", False)

        account.set("space_level", 7)
        account.set("spellcheck", True)
        account.set("roll_summarizer", 1)

        account.set("prestige_level", 9)

        items = values.overall_all_shinies
        
        items.extend(values.all_chess_pieces)
        items.extend(values.all_anarchy_pieces)
        items.extend(values.all_special_breads)
        items.extend(values.all_rare_breads)
        items.extend(values.shadow_emotes)

        items.append(values.ascension_token)
        items.append(values.normal_bread)
        items.append(values.corrupted_bread)
        items.append(values.anarchy_chess)
        items.append(values.chessatron)
        items.append(values.anarchy_chessatron)
        items.append(values.omega_chessatron)
        items.append(values.anarchy_omega_chessatron)
        items.append(values.fuel)
        items.append(values.gem_white)
        items.append(values.ephemeral_token)

        for shop_item in store.all_store_items:
            if issubclass(shop_item, (store.Ephemeral_Upgrade, store.Catalyst)):
                continue
                
            if shop_item.max_level(account) is None:
                continue
            
            if issubclass(shop_item, store.Gambit_shop_Item):
                for _ in shop_item.levels_required:
                    shop_item.do_purchase(account)
            else:
                account.set(shop_item.name, shop_item.max_level(account))


        for emote in items:
            account.set(emote.text, 50000000000)
        

        account.set("fuel_tank", 40000)

        self.json_interface.set_account(user, account, guild = ctx.guild.id)
        await ctx.send("Done.")

    ########################################################################################################################
    #####      ADMIN SYNCHRONIZE_USERNAMES

    @admin.command(
        brief="Re-synchronizes all usernames.",
        help = "Usage: bread admin synchronize_usernames [optional 'manually' flag]"
    )
    @commands.check(verification.is_admin_check)
    async def synchronize_usernames(self, ctx,
            do_manually: typing.Optional[str] = None
        ):

        if do_manually != "manual":
            self.synchronize_usernames_internal()
            await ctx.send("Done.")
            return

        guild = self.bot.get_guild(ctx.guild.id)
        all_members = guild.members

        print(f"member count is {len(all_members)}, theoretical amount is {guild.member_count}")

        if len(all_members) != guild.member_count:
            async for member in guild.fetch_members(limit=150):
                print(member.name)

        # we iterate through all the members and rename the key
        # for member in all_members:
        async for member in guild.fetch_members(limit=5000):
            # make sure they have an account
            # print (f"Checking {member.display_name}")
            if self.json_interface.has_account(member):
                print(f"{member.display_name} has account")
                # get the account
                account = self.json_interface.get_account(member, guild = ctx.guild.id)

                account.values["id"] = member.id
                account.values["username"] = member.name
                account.values["display_name"] = get_display_name(member)
                
                # save the account
                self.json_interface.set_account(member, account, guild = ctx.guild.id)

        # save the database      
        self.json_interface.internal_save()
        
        await ctx.send("Done.")

    ########################################################################################################################
    #####      ADMIN BEQUEATH_CHERRY
    
    @admin.command(
        brief="Remove the cherry.",
        help = "Usage: bread admin bequeath_cherry"
    )
    @commands.check(verification.is_admin_check)
    async def bequeath_cherry(self, ctx):
        if not await self.await_confirmation(ctx):
            return
        
        all_accounts = self.json_interface.get_all_user_accounts(ctx.guild)

        removed = [] # type: list[account.Bread_Account]

        for account in all_accounts:
            if account.has(values.cherry.text):
                account.set(values.cherry.text, 0)
                removed.append(account)

                self.json_interface.set_account(account.get("id"), account, ctx.guild)
        
        await ctx.reply("Done.\n{} affected:\n{}".format(
            utility.write_count(len(removed), 'account'),
            "\n".join([
                f"- {account.get_display_name()} ({account.get('id')})"
                for account in removed
            ])
        ))

    ########################################################################################################################
    #####      ADMIN DO_OPERATION
    
    @admin.command(
        brief="Testing code/database stuff.",
        help = "Usage: bread admin do_operation"
    )
    @commands.check(verification.is_admin_check)
    async def do_operation(self, ctx):

        if not await self.await_confirmation(ctx):
            return
        
        # Go through all accounts in the database and set any instance of High Roller Table to 0.
        # Then add ascension tokens equal to the level of High Roller Table.
        # user_account = self.json_interface.get_account(702477000941502494, 958392331671830579)
        # user_account.set("ephemeral_upgrades", list())
        # self.json_interface.set_account(702477000941502494, user_account, 958392331671830579)
        for guild in self.json_interface.all_guilds:
            for user_account in self.json_interface.get_all_user_accounts(guild):
                if isinstance(user_account.get("ephemeral_upgrades", list()), dict):
                    user_account.set("ephemeral_upgrades", list())
                    self.json_interface.set_account(user_account.user_id, user_account, guild)
                    

        # self.currently_interacting.clear()

        # await self.daily_task()

        ##########################################################
        # Go through all trade hubs and set them to be at [0, 1] #
        # for guild in self.json_interface.all_guilds:
        #     space_data = self.json_interface.get_custom_file("space", guild)
        #     for ascension_key, ascension_value in space_data.items():
        #         if not ascension_key.startswith("ascension"):
        #             continue

        #         for hub_location, hub_data in ascension_value.get("trade_hubs", {}).items():
        #             if hub_data.get("location") == [0, 0]:
        #                 space_data[ascension_key]["trade_hubs"][hub_location]["location"] = [0, 1]
            
        #     self.json_interface.set_custom_file("space", space_data, guild)

        # for guild in self.json_interface.all_guilds:
        #     for user_account in self.json_interface.get_all_user_accounts(guild=guild):
        #         if user_account.get(store.Bling.name) >= 9:
        #             user_account.increment(store.Bling.name, 3) # Account for the space gems being added.
                    
        #             self.json_interface.set_account(user_account.user_id, user_account, guild)
                    
        # When the rocket tiers were shifted and tier 3 was removed this'll correct everyone stats.
        #         space_level = account.get_space_level()
        #         if space_level >= 3:
        #             account.increment("space_level", -1)
                
        #         fr_level = account.get("fuel_research")

        #         if fr_level > 2:
        #             account.increment("fuel_research", -1)
        #             account.increment(values.gem_green, 100)

        #         if fr_level > 2:
        #             account.increment("fuel_research", -1)
        #             account.increment(values.gem_gold, 100)

        #         if fr_level == 2 and space_level < 4:
        #             account.increment("fuel_research", -1)
        #             account.increment(values.gem_purple, 100)

        #         self.json_interface.set_account(account.user_id, account, guild)



        
        # Go through all accounts in the database and set any instance of bling = 6 to 7.
        # This is done because when chessatron bling is added it will be between gold gems
        # and MoaKs. As a result MoaK bling, which was 6 prior to this, is now 7.
        # for guild in self.json_interface.all_guilds:
        #     for account in self.json_interface.get_all_user_accounts(guild):
        #         if account.get("bling") == 6:
        #             account.set("bling", 7)
        #             self.json_interface.set_account(account.get("id"), account, guild)
        
        # go through all accounts and do the operation
        
        # for index in self.json_interface.data["bread"].keys():
        #     if not is_digit(index):
        #         continue
        #     user_account = self.json_interface.get_account(index)
            
        #     if user_account.get("LC_booster") == 1:
        #         user_account.increment(values.gem_gold.text, 1)

        #     self.json_interface.set_account(index, user_account)

            # #now we check each dough boost and increase it
            # for special_bread in values.all_special_breads:
            #     if user_account.get_dough_boost_for_item(special_bread) == 1:
            #         user_account.set_dough_boost_for_item(special_bread, 2)

            # for rare_bread in values.all_rare_breads:
            #     if user_account.get_dough_boost_for_item(rare_bread) == 2:
            #         user_account.set_dough_boost_for_item(rare_bread, 4)

            # for chess_piece_black in values.chess_pieces_black_biased:
            #     if user_account.get_dough_boost_for_item(chess_piece_black) == 10:
            #         user_account.set_dough_boost_for_item(chess_piece_black, 20) 
            
            # for chess_piece_white in values.chess_pieces_white_biased:
            #     if user_account.get_dough_boost_for_item(chess_piece_white) == 20:
            #         user_account.set_dough_boost_for_item(chess_piece_white, 40)

        # user_account = self.json_interface.get_account(ctx.author)
        # portfolio_value = user_account.get_portfolio_value()
        # await ctx.reply(f"Your portfolio value is {portfolio_value}")

        # load_dotenv()
        # IS_PRODUCTION = getenv('IS_PRODUCTION')
        # print("IS_PRODUCTION is: "+IS_PRODUCTION)
        # if IS_PRODUCTION == "True":
        #     print("This is a production server")
            
        # if IS_PRODUCTION == "False":
        #     print("This is a development server")
            
        # for index in self.json_interface.data["bread"].keys():
        #     if not is_digit(index):
        #         continue # skip the custom accounts
        #     user_account = self.json_interface.get_account(index)
        #     if user_account.has("one_of_a_kind"):
        #         amount = user_account.get(values.anarchy_chess.text)
        #         user_account.set("one_of_a_kind", 0)
        #     if user_account.has(values.anarchy.text):
        #         amount = user_account.get(values.anarchy.text)
        #         user_account.increment("one_of_a_kind", amount)
        #     if user_account.has(values.horsey.text):
        #         amount = user_account.get(values.horsey.text)
        #         user_account.increment("one_of_a_kind", amount)
        #     if user_account.has(values.holy_hell.text):
        #         amount = user_account.get(values.holy_hell.text)
        #         user_account.increment("one_of_a_kind", amount)

        #     self.json_interface.set_account(index, user_account)

        


        # # what we're going to do is reset highest_roll to a sensible value
        # JSON_cog = self.bot.get_cog("JSON")
        # cabinet = JSON_cog.get_filing_cabinet("bread")

        # # we get the guild and then all the members in it
        # guild = ctx.guild
        # all_members = guild.members

        # # we then iterate through all the members and reset their highest_roll to a sensible amount
        # for member in all_members:
        #     if self.json_interface.has_account(member):
        #         account = self.json_interface.get_account(member)
        #         if account.has("highest_roll"):
        #             # first set it to zero
        #             account.set("highest_roll", 0)

        #             #then, in sequence, we set it to the highest value of all the special ones they've found
        #             if account.has("ten_breads"):
        #                 account.set("highest_roll", 10)
        #             if account.has("eleven_breads"):
        #                 account.set("highest_roll", 11)
        #             if account.has("twelve_breads"):
        #                 account.set("highest_roll", 12)
        #             if account.has("thirteen_breads"):
        #                 account.set("highest_roll", 13)

        #         # finally, we set the account back into the database
        #         self.json_interface.set_account(member, account)
        
        # self.json_interface.internal_save()

        # await ctx.send("Done.")

        # JSON_cog = self.bot.get_cog("JSON")
        # cabinet = JSON_cog.get_filing_cabinet("bread", create_if_nonexistent=False)
        # print (f"cabinet is {cabinet}")
        # # bread_files = self.json_interface.data["bread"]
        # for key in cabinet.keys():
        #     file = cabinet[key]
        #     print (f"file is {file}")
        #     if "lifetime_dough" in file.keys():
        #         pass
        #     else:
        #         file["lifetime_dough"] = file["total_dough"]
        # JSON_cog.set_filing_cabinet("bread", cabinet)
        
        
        # #await ctx.send("Do not use this, it does not work.")
        # bread_files = self.json_interface.data["bread_count"]

        # JSON_cog = self.bot.get_cog("JSON")
        # cabinet = JSON_cog.get_filing_cabinet("bread", create_if_nonexistent=True)

        # for key in bread_files.keys():
        # #for file in files:
        #     bread_file = bread_files[key]
        #     cabinet[key] = bread_file
        #     pass
        # pass
        # JSON_cog.set_filing_cabinet("bread", cabinet)

        # old_data = self.json_interface.data["archived_bread_count"]
        # archive_cabinet = JSON_cog.get_filing_cabinet("archived_bread_count", create_if_nonexistent=True)
        # JSON_cog.set_filing_cabinet("archived_bread_count", old_data)

        await ctx.send("Done.")
    
    @admin.command(
        brief="Runs the space tick.",
        help = "Usage: bread admin run_space_tick"
    )
    @commands.check(verification.is_admin_check)
    async def run_space_tick(self, ctx):
        self.space_tick()
        await ctx.reply("Done.")

    ########################################################################################################################
    #####      ADMIN SAVE / ADMIN LOAD
    
    @admin.command(
        brief="Loads the database from file.",
        help = "Usage: bread admin load"
    )
    @commands.is_owner()
    async def load(self, ctx):

        self.json_interface.internal_load()
        #print("test, 1 arg")
        await ctx.send("Done.")

    @admin.command(
        brief="Saves the database to file.",
        help = "Usage: bread admin save"
    )
    @commands.is_owner()
    async def save(self, ctx):
        self.json_interface.internal_save()
        await ctx.send("Done.")

    def internal_save(self, json_cog = None):
        print("Bread_cog save has been called")
        self.json_interface.internal_save(json_cog)

    ########################################################################################################################
    #####      ADMIN SET_ANNOUNCEMENT_CHANNEL

    @admin.command(
        brief="Sets the announcement channel.",
        help = "Usage: bread admin set_announcement_channel [optional channel]",
        aliases = ["set_announce_channel"]
    )
    @commands.check(verification.is_admin_check)
    async def set_announcement_channel(self, ctx,
            channel: typing.Optional[discord.TextChannel] = None
        ):
        if channel is None:
            channel = ctx.channel

        guild_info = self.json_interface.get_guild_info(ctx.guild.id)
        guild_info["announcement_channel"] = channel.id
        self.json_interface.set_guild_info(guild=ctx.guild.id, guild_info=guild_info)

        await ctx.send(f"Done. Announcements will be made in {channel.mention}.")


    ########################################################################################################################
    #####      ADMIN STONK_FLUCTUATE

    @admin.command(
        brief="Runs a stonk tick.",
        help = "Usage: bread admin stonk_fluctuate"
    )
    @commands.check(verification.is_admin_check)
    async def stonk_fluctuate(self, ctx):
        self.stonk_fluctuate_internal()
        await self.stonks_announce() #TODO: test this shit
        await ctx.send("Done.")
        #await ctx.invoke(self.stonks)

    ########################################################################################################################
    #####      ADMIN STONK_RESET

    @admin.command(
        brief="Resets stonk values to default.",
        help = "Usage: bread admin stonk_reset"
    )
    @commands.check(verification.is_admin_check)
    async def stonk_reset(self, ctx):
        self.stonk_reset_internal(guild = ctx.guild.id)
        await ctx.invoke(self.stonks)

    ########################################################################################################################
    #####      ADMIN STONK_SPLIT

    @admin.command(
        brief="Splits the given stonk.",
        help = "Usage: bread admin stonk_split [stonk name]"
    )
    @commands.check(verification.is_admin_check)
    async def stonk_split(self, ctx,
            stonk_name: typing.Optional[str]
        ):
        stonk_text = values.get_emote_text(stonk_name)

        stonks_file = self.json_interface.get_custom_file("stonks", guild = ctx.guild.id)

        if stonk_text not in stonks_file:
            await ctx.reply("I don't recognize that item.")
            return
        
        self.stonk_split_internal(stonk_text, guild=ctx.guild.id)
        await ctx.reply("Done.")

    ########################################################################################################################
    #####      ADMIN ADD_CHESS_SET

    @admin.command(
        brief="Gives a chess set to a member.",
        help = "Usage: bread admin add_chess_set [optional member] [optional amount]"
    )
    @commands.check(verification.is_admin_check)
    async def add_chess_set(self, ctx,
            target: typing.Optional[discord.Member],
            count: typing.Optional[int] = 1
        ):
        if target is None:
            target = ctx.author

        user_account = self.json_interface.get_account(target, guild = ctx.guild.id)
        full_chess_set = values.chess_pieces_black_biased+values.chess_pieces_white_biased

        # add all pieces to the account
        for emote in full_chess_set:
            user_account.increment(emote.text, count)

        self.json_interface.set_account(target, user_account, guild = ctx.guild.id)

        await ctx.reply("Done.")

    ########################################################################################################################
    #####      ADMIN ADD_ANARCHY_SET

    @admin.command(
        brief="Gives an anarchy set to a member.",
        help = "Usage: bread admin add_anarchy_set [optional member] [optional amount]"
    )
    @commands.check(verification.is_admin_check)
    async def add_anarchy_set(self, ctx,
            target: typing.Optional[discord.Member],
            count: typing.Optional[int] = 1
        ):
        if target is None:
            target = ctx.author

        user_account = self.json_interface.get_account(target, guild = ctx.guild.id)
        full_chess_set = values.anarchy_pieces_black_biased + values.anarchy_pieces_white_biased

        # add all pieces to the account
        for emote in full_chess_set:
            user_account.increment(emote.text, count)

        self.json_interface.set_account(target, user_account, guild = ctx.guild.id)

        await ctx.reply("Done.")

    ########################################################################################################################
    #####      ADMIN GENERATE_GALAXY

    @admin.command(
        brief="Gives an anarchy set to a member.",
        help = "Usage: bread admin add_anarchy_set [optional member] [optional amount]"
    )
    @commands.check(verification.is_admin_check)
    async def generate_galaxy(self, ctx,
            ascension: typing.Optional[int]
        ):
        if ascension is None:
            await ctx.reply("Please provide the ascension to generate the map for.")
            return
        
        if not await self.await_confirmation(
                ctx = ctx,
                force = True,
                message = "Are you really sure you want to do this? It will greatly increase the size of the database and will take some time to complete."
            ):
            return
        
        seed = self.json_interface.get_ascension_seed(ascension, ctx.guild.id)
        
        for x_coord in range(space.MAP_SIZE):
            for y_coord in range(space.MAP_SIZE):
                space.get_galaxy_coordinate(
                    json_interface = self.json_interface,
                    guild = ctx.guild.id,
                    galaxy_seed = seed,
                    ascension = ascension,
                    xpos = x_coord,
                    ypos = y_coord,
                    load_data = True
                )
            print(f"Generating the entire a{ascension} galaxy as requested by {ctx.author.name}. Progress: {x_coord + 1}/256.")
        
        await ctx.reply("Done.")

    ########################################################################################################################
    #####      ADMIN INCREASE_PRESTIGE

    @admin.command(
        brief="Increase prestige level of member.",
        help = "Usage: bread admin increase_prestige [optional member]"
    )
    @commands.check(verification.is_admin_check)
    async def increase_prestige(self, ctx,
            target: typing.Optional[discord.Member]
        ):
        if await self.await_confirmation(ctx) is False:
            return
        
        if target is None:
            target = ctx.author

        user_account = self.json_interface.get_account(target, guild = ctx.guild.id)
        user_account.increase_prestige_level()

        self.json_interface.set_account(target, user_account, guild = ctx.guild.id)

        await ctx.reply(f"Done. Prestige level is now {user_account.get_prestige_level()}.")

    ########################################################################################################################
    #####      ADMIN ADD_ADMIN

    @admin.command(
        brief="Add approved admin.",
        help = "Usage: bread admin add_admin [member]"
    )
    @commands.is_owner()
    async def add_admin(self, ctx, target: typing.Optional[discord.Member]):
        if target is None:
            await ctx.reply("Please provide a user to add as an admin for this guild.")
            return
        
        admins = self.json_interface.get_approved_admins(ctx.guild)

        if str(target.id) in admins:
            await ctx.reply("That user is already an admin in this guild.")
            return
        
        print(f"{ctx.author} is adding {target} as an approved admin in {ctx.guild} ({ctx.guild.id})")
        
        admins.append(str(target.id))

        guild_info = self.json_interface.get_guild_info(ctx.guild)
        guild_info["approved_admins"] = admins
        self.json_interface.set_guild_info(guild=ctx.guild.id, guild_info=guild_info)

        await ctx.reply("Done.")

    ########################################################################################################################
    #####      ADMIN REMOVE_ADMIN

    @admin.command(
        brief="Remove approved admin.",
        help = "Usage: bread admin remove_admin [member]"
    )
    @commands.is_owner()
    async def remove_admin(self, ctx, target: typing.Optional[discord.Member]):
        if target is None:
            await ctx.reply("Please provide a user to remove admin permissions for this guild.")
            return
        
        admins = self.json_interface.get_approved_admins(ctx.guild)

        if str(target.id) not in admins:
            await ctx.reply("That user isn't an admin.")
            return
        
        print(f"{ctx.author} is removing admin permissions from {target} in {ctx.guild} ({ctx.guild.id})")
        
        admins.remove(str(target.id))

        guild_info = self.json_interface.get_guild_info(ctx.guild)
        guild_info["approved_admins"] = admins
        self.json_interface.set_guild_info(guild=ctx.guild.id, guild_info=guild_info)

        await ctx.reply("Done.")

    ########################################################################################################################
    #####      ADMIN ADMIN_LIST

    @admin.command(
        brief="Approved admins list.",
        help = "Usage: bread admin admin_list"
    )
    @commands.check(verification.is_admin_check)
    async def admin_list(self, ctx):
        admins = self.json_interface.get_approved_admins(ctx.guild)

        if len(admins) == 0:
            await ctx.reply("This guild has no admins currently.")
            return
        
        members = [get_display_name(discord.utils.find(lambda m: str(m.id) == admin, ctx.guild.members)) for admin in admins]

        await ctx.reply("Current admins:\n" + ", ".join(members))

    ########################################################################################################################
    #####      STRING FORMATTING

    
    def write_number_of_times(number: int) -> str:
        """Write the amount of times, for a number.
        
        For example, `0` will return `zero times`, `1` will return `once`, and something like `10` will return `10 times`."""
        number = parse_int(number)
        if number == 0:
            return "zero times"
        elif number == 1:
            return "once"
        elif number == 2:
            return "twice"
        else:
            return str(number) + " times"

    def format_chess_pieces(
            self: typing.Self,
            file: dict
        ) -> str:
        """Returns a string of the formatted version of the given file's chess pieces."""
        output = ""

        ###############################################################
        
        newline = False
        #make white setup
        #rook 1 
        if white_rook in file.keys() and file[white_rook] >= 1:
            output += white_rook + " "
            newline = True

        #knight 1 white_knight
        if white_knight in file.keys() and file[white_knight] >= 1:
            output += white_knight + " "
            newline = True

        #bishop 1 white_bishop
        if white_bishop in file.keys() and file[white_bishop] >= 1:
            output += white_bishop + " "
            newline = True

        #queen white_queen
        if white_queen in file.keys() and file[white_queen] >= 1:
            output += white_queen + " "
            newline = True

        #king white_king
        if white_king in file.keys() and file[white_king] >= 1:
            output += white_king + " "
            newline = True

        #bishop 2 white_bishop
        if white_bishop in file.keys() and file[white_bishop] >= 2:
            output += white_bishop + " "
            newline = True

        #knight 2 white_knight
        if white_knight in file.keys() and file[white_knight] >= 2:
            output += white_knight + " "
            newline = True

        #rook 2 white_rook
        if white_rook in file.keys() and file[white_rook] >= 2:
            output += white_rook + " "
            newline = True

        if newline:
            output += "\n"
        
        ###############################################################

        #make white pawns
        if white_pawn in file.keys() and file[white_pawn] >= 1:
            for i in range(0, min(8, file[white_pawn])):
                output += white_pawn + " "
            output += "\n"

        #make black pawns
        if black_pawn in file.keys() and file[black_pawn] >= 1:
            for i in range(0, min(8, file[black_pawn])):
                output += black_pawn + " "
            output += "\n"

        ###############################################################

        newline = False
        #make black setup
        #rook 1 black_rook
        if black_rook in file.keys() and file[black_rook] >= 1:
            output += black_rook + " "
            newline = True

        #knight 1 black_knight
        if black_knight in file.keys() and file[black_knight] >= 1:
            output += black_knight + " "
            newline = True

        #bishop 1 black_bishop
        if black_bishop in file.keys() and file[black_bishop] >= 1:
            output += black_bishop + " "
            newline = True

        #queen black_queen
        if black_queen in file.keys() and file[black_queen] >= 1:
            output += black_queen + " "
            newline = True

        #king black_king
        if black_king in file.keys() and file[black_king] >= 1:
            output += black_king + " "
            newline = True

        #bishop 2 black_bishop
        if black_bishop in file.keys() and file[black_bishop] >= 2:
            output += black_bishop + " "
            newline = True

        #knight 2 black_knight
        if black_knight in file.keys() and file[black_knight] >= 2:
            output += black_knight + " "
            newline = True

        #rook 2 black_rook
        if black_rook in file.keys() and file[black_rook] >= 2:
            output += black_rook + " "
            newline = True

        if newline:
            output += "\n"
        
        return output
    
    def format_anarchy_pieces(
            self: typing.Self,
            account_values: dict
        ) -> str:
        """Returns a string for the formatted anarchy chess pieces of the given account data."""

        def remove_double_spaces(string: str) -> str:
            while "  " in string:
                string = string.replace("  ", " ")
            
            return string
        
        lines = []
        
        components = [["" for _ in range(8)] for _ in range(2)]

        white_minor_pieces = [values.anarchy_white_rook, values.anarchy_white_knight, values.anarchy_white_bishop]
        black_minor_pieces = [values.anarchy_black_rook, values.anarchy_black_knight, values.anarchy_black_bishop]

        for index, piece in enumerate(white_minor_pieces + black_minor_pieces):
            amount = account_values.get(piece.text, 0)
            if amount >= 1:
                components[index // 3][index % 3] = piece.text
            if amount >= 2:
                components[index // 3][7 - (index % 3)] = piece.text

        for index, piece in enumerate([values.anarchy_white_queen, values.anarchy_white_king, values.anarchy_black_queen, values.anarchy_black_king]):
            amount = account_values.get(piece.text, 0)
            if amount >= 1:
                components[index // 2][(index % 2) + 3] = piece.text
        
        lines.append(remove_double_spaces(" ".join(components[0]).strip()))

        pawn = min(account_values.get(values.anarchy_white_pawn.text, 0), 8)
        lines.append((pawn * (values.anarchy_white_pawn.text + " ")).strip())

        pawn = min(account_values.get(values.anarchy_black_pawn.text, 0), 8)
        lines.append((pawn * (values.anarchy_black_pawn.text + " ")).strip())
        
        lines.append(remove_double_spaces(" ".join(components[1]).strip()))

        return "\n".join(lines)
        


    

bread_cog_ref = None

bot_ref = None

async def setup(bot: commands.Bot):
    
    importlib.reload(emoji)
    importlib.reload(verification)
    importlib.reload(values)
    importlib.reload(account)
    importlib.reload(gamble)
    importlib.reload(rolls)
    importlib.reload(store)
    importlib.reload(utility)
    importlib.reload(alchemy)
    importlib.reload(stonks)
    importlib.reload(space)
    importlib.reload(generation)
    importlib.reload(projects)

    bread_cog = Bread_cog(bot)
    await bot.add_cog(bread_cog)

    global bread_cog_ref 
    bread_cog_ref = bread_cog
    
    global bot_ref
    bot_ref = bot

    try:
        #Bread_cog.internal_load(bot)
        bread_cog.json_interface.internal_load()
    except BaseException as err:
        print(err)
    
    bread_cog.scramble_random_seed()
    #bot.add_cog(Chess_game(bot)) #do we want to actually have this be a *cog*, or just a helper class?

#seems mostly useless since we can't call anything async
def teardown(bot: commands.Bot):
    print('bread cog is being unloaded.')
    #print("bot is "+str(bot))
    
    #print("bread cog ref is "+str(bread_cog_ref))
    try:
        print("Saving bread data.")
        bread_cog_ref.internal_save()
        print("Done.")
    except BaseException as err:
        print("An error occurred saving bread data.")
        print(traceback.format_exc())

    #Bread_cog.internal_save(bot)
    #await bot.graceful_shutdown()
    #Chess_bot.graceful_shutdown(bot)
