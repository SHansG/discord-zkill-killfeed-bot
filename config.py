from typing import AnyStr
import json
import os
from addons import Settings, TOKENS
from pymongo import MongoClient
from db.auto_create_db import create_db
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
settings_file_path = os.path.join(ROOT_DIR, "settings.json")
solarsystems_path = f'{ROOT_DIR}/res/'

# URLs
websocket_url = f"wss://zkillboard.com/websocket/"

# dicts
# TODO: assign data to dicts using function
id_system_df = pd.read_csv(f'{ROOT_DIR}/res/mapSystems_filtered.csv')
# id_system_dict = id_system_df.set_index('solarSystemID').to_dict()['solarSystemName']
system_id_dict = id_system_df.set_index('solarSystemName').to_dict()['solarSystemID']

id_constellation_df = pd.read_csv(f'{ROOT_DIR}/res/mapConstellation_filtered.csv')
# id_constellation_dict = id_constellation_df.set_index('constellationID').to_dict()['constellationName']
constellation_id_dict = id_constellation_df.set_index('constellationName').to_dict()['constellationID']

id_region_df = pd.read_csv(f'{ROOT_DIR}/res/mapRegions_filtered.csv')
# id_region_dict = id_region_df.set_index('regionID').to_dict()['regionName']
region_id_dict = id_region_df.set_index('regionName').to_dict()['regionID']

id_group_df = pd.read_csv(f'{ROOT_DIR}/res/groups_filtered_final.csv')
# id_group_dict = id_group_df.set_index('groupID').to_dict()['groupName']
group_id_dict = id_group_df.set_index('groupName').to_dict()['groupID']

id_type_df = pd.read_csv(f'{ROOT_DIR}/res/types_filtered_final.csv')
type_id_dict = id_type_df.set_index('typeName').to_dict()['typeID']

# officer npc group_ids
# this is probably temporary solution but I dont have better idea how to filter
# officer npcs due to them not having "faction_id" in the killmail jsons
special_npc_group_id_df = pd.read_csv(f'{ROOT_DIR}/res/special_npc_group_ids.csv', index_col=0)
special_npc_group_id_list = special_npc_group_id_df['groupID'].to_list()

# print(type_id_dict)
filter_location_type_dict = {
    "Region":region_id_dict,
    "Constellation":constellation_id_dict,
    "System":system_id_dict,
    "None": {"No Filter": 0}
}

filter_entity_type_dict = {
    "Group": group_id_dict,
    "Type": type_id_dict,
    "No Filter": {"No Filter":0}
}

filter_attacker_npc_dict = {
    "Yes": 1,
    "No": 0
}

# location lookup dict for filter logic in zkill cog
merged_regions_constellations_systems_df = pd.read_csv(f"{ROOT_DIR}/res/map_regions_constellations_systems_merged.csv", index_col=0)
location_lookup_dict = merged_regions_constellations_systems_df.set_index('solarSystemID').to_dict(orient='index')

# entity lookup dict for filter logic in zkill cog
merged_groups_types_df = pd.read_csv(f"{ROOT_DIR}/res/merged_groupID_typeID.csv", index_col=0)
entity_lookup_dict = merged_groups_types_df.set_index('typeID').to_dict(orient='index')

#--- API Keys ---
tokens=TOKENS()

#--- DB connection check ---
try:
    mongodb = MongoClient(host=tokens.mongodb_url)
    mongodb.server_info()
    if tokens.mongodb_name not in mongodb.list_database_names():
        print(f"{tokens.mongodb_name} does not exist in your mongodb")
        # assuming you have already configured mongodb below function should work just fine
        create_db(mongodb, tokens.mongodb_name)
    print("Succesfully connected to MongoDB!")
except Exception as e:
    raise Exception("Not able to connect MongoDB! Reason:", e)

SETTINGS_DB = mongodb[tokens.mongodb_name]['Settings']

# check for settings.json
if not os.path.exists(settings_file_path):
    raise Exception("No settings file!")

# cache var
settings: Settings
GUILD_SETTINGS: dict[int, dict[str, AnyStr]] = {}

def load_guilds_settings(guild_id_list: list) -> None:
    """Load guild settings into cache"""
    for guild_id in guild_id_list:
        settings_dict=SETTINGS_DB.find_one({"_id":guild_id})
        if not settings_dict:
            SETTINGS_DB.insert_one({**{"_id": guild_id}, **settings.settings_dict})
            settings_dict = settings.settings_dict
        GUILD_SETTINGS[guild_id] = settings_dict or {}

# TODO: function below will probably need to be refactored
# as function load_guilds_settings does the get settings work
# and get_settings() should get the server config from cache var
def get_settings(guild_id: int) -> dict:
    settings_dict = GUILD_SETTINGS.get(guild_id, None)
    if not settings_dict:
        settings_dict = SETTINGS_DB.find_one({"_id":guild_id})
        if not settings_dict:
            SETTINGS_DB.insert_one({**{"_id": guild_id}, **settings.settings_dict})
            settings_dict = settings.settings_dict
        GUILD_SETTINGS[guild_id] = settings_dict or {}
    return settings_dict

def update_settings(guild_id:int, data: dict, mode="set") -> bool:
    settings_dict = get_settings(guild_id)

    for key, value in data.items():
        if settings_dict.get(key) != value:
            match mode:
                case "set":
                    GUILD_SETTINGS[guild_id][key] = value
                case "unset":
                    GUILD_SETTINGS[guild_id].pop(key)
                case _:
                    return False
    
    result = SETTINGS_DB.update_one({"_id":guild_id}, {f"${mode}":data})
    return result.modified_count > 0

def add_settings(guild_id: int) -> bool:
    result = SETTINGS_DB.insert_one({**{"_id": guild_id}, **settings.settings_dict})
    settings_dict = settings.settings_dict
    GUILD_SETTINGS[guild_id] = settings_dict
    return result.acknowledged

def delete_settings(guild_id: int) -> bool:
    GUILD_SETTINGS.pop(guild_id)
    result = SETTINGS_DB.delete_one({"_id":guild_id})
    return result.deleted_count > 0

def open_json(path: str) -> dict:
    try:
        with open(os.path.join(ROOT_DIR, path), encoding="utf8") as json_file:
            return json.load(json_file)
    except:
        return {}

def update_json(path: str, new_data: dict) -> None:
    data = open_json()
    if not data: 
        return
    
    data.update(new_data)

    with open(os.path.join(ROOT_DIR, path), "w") as json_file:
        json.dump(data, json_file, indent=4)

def init() -> None:
    global settings
    json = open_json(settings_file_path)
    if json is not None:
        settings = Settings(json)