import json
import math
import os
import random
from datetime import datetime

import discord
from discord import Member, VoiceChannel

import src.core.core as core


def approved_role_user(interaction: discord.Interaction) -> bool:
    """returns if user is in configs['Role Manager Handles'] or has a role present in ['Role Manager Roles']?"""
    return check_approved_user(interaction, 'Role Manager')


def approved_channel_user(interaction: discord.Interaction) -> bool:
    """returns if user is in configs['Channel Manager Handles'] or has a role present in ['Channel Manager Roles']?"""
    return check_approved_user(interaction, 'Channel Manager')


def check_approved_user(interaction: discord.Interaction, user_check_type: str) -> bool:
    """Returns whether the user has permission to use the command"""
    filename = f'configs-{interaction.guild_id}'
    data = get_config(filename)

    # if both fields are empty, return true
    if not data[f'{user_check_type} Handles'] and not data[f'{user_check_type} Roles']:
        return True

    if data[f'{user_check_type} Handles'] and interaction.user.name in data[f'{user_check_type} Handles']:
        return True

    if data[f'{user_check_type} Roles']:
        for role in interaction.user.roles:
            if role.id in data[f'{user_check_type} Roles']:
                return True

    # if all else fails, are they an admin?
    return interaction.user.guild_permissions.administrator


def get_config(filename: str) -> dict:
    """Obtains config file. Will generate missing files if none are present"""
    if os.path.isfile(f'{core.PATH}/config/{filename}.json'):
        with open(f'{core.PATH}/config/{filename}.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return check_config_integrity(filename)


def get_config_variable(data: dict, entry: str, filename: str, servername: str = None):
    """Function for obtaining a single entry in a dictionary, if it is not present it will generate it"""
    return check_config_entry(data, entry, filename, servername)[entry]


def check_config_entry(data: dict, entries: str | tuple | list, filename: str, servername: str = None) -> dict:
    """Alternative to "if entry in dict" where potential missing data will be replaced.
     - data: the json data being checked
     - entries: list of entities to check for. Also accepts single entity string
     - filename: name of file data was originally obtained from, used if data is missing
     - servername: (Optional) name of the discord server. Used for configs-id.json
    Returns either original or fixed dict"""
    # converts strings into tuple
    if isinstance(entries, str):
        entries = entries,
    # iterate through list, upon a single missing entry, generate all missing data
    for entry in entries:
        if entry not in data:
            logger(f'Missing entry "{entry}" in {filename}.json. Adding missing entries to the file')
            return check_config_integrity(filename, servername, entry)
    return data


def check_config_integrity(filename: str, servername: str = None, entry: str = None) -> dict | None:
    """File that ensures all necessary entries are present in the config. Servername variable recommended for configs.json"""
    # default configs.json data
    if filename.startswith('configs'):
        filedata = {
            "Server Name": servername,
            "White List": True, "Use Alias": True, "Active Icon": "📊",
            "Priority Order": True,
            "Roles List": {
                "First Role Name": "1st Alias",
                "Second Role Name": "2nd Alias",
                "Third Role Name": "3rd Alias"

            },
            "Fill Character": "\u2588", "Partial Character": "\u2592", "Empty Character": "\u2591",
            "Role Manager Handles": [],
            "Role Manager Roles": [],
            "Channel Manager Handles": [],
            "Channel Manager Roles": []
        }

    # default channels.json data
    elif filename == 'channels':
        filedata = {"Channels": {}, "Role Bot": {}}

    # otherwise, ignore
    else:
        raise FileNotFoundError(f'The file "{filename}" is not a recognised type')

    # if the file exists
    if os.path.isfile(f'{core.PATH}/config/{filename}.json'):

        # read the file and check for missing entries. If any present then change = True
        with open(f'{core.PATH}/config/{filename}.json', 'r') as f:
            old_data = json.load(f)

        change = False
        for entry in filedata:
            if entry not in old_data:
                change = True
                old_data[entry] = filedata[entry]

    # if the file does not currently exist, write the default data to the file
    else:
        change = True
        old_data = filedata

    # if changes have been made, overwrite the file with the modified data
    if change:
        with open(f'{core.PATH}/config/{filename}.json', 'w') as f:
            json.dump(old_data, f, indent=4)

    if entry and entry not in old_data:
        raise IndexError(f'Requested entry "{entry}" not present in config type: {filename}.json')

    return old_data


def save_config(filename: str, data: dict):
    """Saves to json config file"""
    with open(f'{core.PATH}/config/{filename}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def get_valid_roles(member: Member) -> list:
    """Obtains list of all role names recognised in the config file"""
    config_roles = get_config(f'configs-{member.guild.id}')

    # obtain lists
    white_list = config_roles["White List"]
    roles_list = config_roles["Roles List"]

    # initialise roles list, this will be the roles used in the final status
    found_roles = []

    # iterate through all roles
    for role in member.roles:

        # ignore everyone role
        if role.name == '@everyone':
            continue

        # if using a whitelist and the role is found in the given config list, add
        if white_list and role.name in roles_list:
            found_roles.append(role.name)
        # if a blacklist is used and the role is not in the given list, add
        elif not white_list and role.name not in roles_list:
            found_roles.append(role.name)

    return found_roles


async def edit_voice_status(channel: VoiceChannel):
    """Function that edits the voice channel status"""
    # create dictionary of roles
    roles_count = {}

    filename = f'configs-{channel.guild.id}'

    channel_data = get_config('channels')
    config_data = get_config(filename)

    # get valid channel ids
    config_channels = get_config_variable(channel_data, 'Channels', 'channels')
    # get icon to check for
    icon = config_data['Active Icon']

    # if the channel is valid and in whitelist/ends with icon
    if channel and (channel.id in config_channels.values() or channel.name.endswith(icon)):
        # for each member present in the channel
        for member in channel.members:

            # iterate through all valid roles and add to the counter
            for role in get_valid_roles(member):
                if role in roles_count:
                    roles_count[role] += 1
                else:
                    roles_count[role] = 1

    # gets biggest role
    if roles_count:
        roles = [key for key, value in sorted(roles_count.items(), key=lambda item: item[1], reverse=True)]

        # should the order be based on random choice in the event of a tie?
        if config_data['Priority Order']:
            role = roles[0]
        else:
            random_roles = []
            for r in roles:
                if roles_count[r] == roles_count[roles[-1]]:
                    random_roles.append(r)
                else:
                    break
            role = random.choice(random_roles)

    else:
        return

    # gets percent of users with this role
    percent = math.floor((roles_count[role] * 100) / len(channel.members))

    # generate "loading bar"
    return_string = config_data['Fill Character'] * (percent // 10)
    empty_slots = 10 - (percent // 10)
    # if not perfectly divisible by 10
    if percent % 10 != 0:
        return_string += config_data['Partial Character']
        empty_slots -= 1
    # fill the rest with the space character
    return_string += config_data["Empty Character"] * empty_slots

    # gets alias if applicable
    if config_data["White List"] and config_data["Use Alias"]:
        role = config_data["Roles List"][role] if config_data["Roles List"][role] else role

    return_string += f' {percent}% {role}'

    await channel.edit(status=return_string)


def logger(message: str, end: str = '\n'):
    print(datetime.now().strftime("%H:%M:%S"), '\t', message, end=end)
