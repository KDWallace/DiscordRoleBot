import discord
from discord import app_commands, Member, VoiceState, VoiceChannel, HTTPException, RawReactionActionEvent, Guild, \
    Colour, Message
from discord.app_commands import TransformerError
from discord.ext import commands

from src.core.core import setup
from src.core.util import approved_role_user, approved_channel_user, get_config, check_config_integrity, \
    save_config, edit_voice_status, logger
from src.core.update import __VERSION__, update_routine, check_version

# stores the intents for the bot to use. To make full use of this, some of the intents must be set in the developers
# portal for discord
intents = discord.Intents(
    discord.Intents.voice_states.flag + discord.Intents.reactions.flag + discord.Intents.guilds.flag + discord.Intents.members.flag)
# prefix needed before a command is called (obtained from CONFIG.py)
client = commands.Bot(command_prefix=commands.when_mentioned_or('/'), intents=intents)


######################################################################################################################
# Functions
######################################################################################################################
async def reloadrolesmessage(interaction: discord.Interaction, messagelink: str, botonly: bool = True):
    try:
        config_data = get_config('channels')
        message = await removeallreactions(interaction, messagelink, botonly)
        for role in config_data['Role Bot'][messagelink]['Roles']:
            emote = role["Role Emote"] if not isinstance(role['Role Emote'],
                                                         int) else await interaction.guild.fetch_emoji(
                role['Role Emote'])
            await message.add_reaction(emote)
        return True
    except Exception:
        return False


async def removeallreactions(interaction: discord.Interaction, messagelink: str, botonly: bool = True):
    config_data = get_config('channels')
    if messagelink not in config_data['Role Bot']:
        await interaction.response.send_message('Message does not appear to be stored', ephemeral=True)
        return
    channel = await interaction.guild.fetch_channel(int(messagelink.split('/')[-2]))
    message = await channel.fetch_message(int(messagelink.split('/')[-1]))
    if not botonly:
        await message.clear_reactions()
    else:
        for reaction in message.reactions:
            await message.remove_reaction(reaction, client.user)
    return message


######################################################################################################################
# Events
######################################################################################################################
@client.event
async def on_ready():
    """Function called on successful bot boot-up"""
    synced = await client.tree.sync()

    # check integrity of configs
    print('Checking integrity of configs...\n - Checking channels.json...', end='')
    check_config_integrity('channels')
    print('Done')
    for guild in client.guilds:
        print(f' - Checking configs-{guild.id}.json ({guild.name})...', end='')
        check_config_integrity(f'configs-{guild.id}', guild.name)
        print('Done')

    print(f'Synced {len(synced)} slash commands')
    for command in synced:
        print(f'\t\t/{command}')

    logger(f' - {client.user.name} is online!')
    print('-' * 76, "\nSource: https://github.com/KDWallace/DiscordRoleBot/")
    await client.loop.create_task(update_routine(client))


@client.event
async def on_guild_join(guild: Guild):
    """Function for joining new server. Used to create a new config file"""
    logger(f'Joined guild: {guild.name}\n - Generating file "configs-{guild.id}.json"...', end='')
    check_config_integrity(f'configs-{guild.id}', guild.name)
    print('Done')


# checks user messages
@client.event
async def on_message(ctx: Message):
    """Function called on someone messaging"""
    # ignores all messages by any bots, including itself
    if ctx.author.bot:
        return

    # processes commands
    await client.process_commands(ctx)
    pass


@client.event
async def on_member_update(before: Member, after: Member):
    """Function called on member update, used to detect role update"""
    if before.roles != after.roles and after.voice and after.voice.channel:
        await edit_voice_status(after.voice.channel)


@client.event
async def on_raw_reaction_add(payload: RawReactionActionEvent):
    """Function called on user reacting to a message"""
    role_data = get_config('channels')
    messagelink = f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}"
    if "Role Bot" in role_data and messagelink in role_data["Role Bot"]:
        emoji = str(payload.emoji)  # payload.emoji.id if payload.emoji.is_custom_emoji() else str(payload.emoji)
        for role in role_data["Role Bot"][messagelink]["Roles"]:
            # added or statement for backward compatibility
            if role["Role Emote"] == emoji or (
                    payload.emoji.is_custom_emoji() and payload.emoji.id == role["Role Emote"]):
                user = payload.member
                guild = await client.fetch_guild(payload.guild_id)
                for guild_role in guild.roles:
                    if guild_role.id == role["Role ID"]:
                        if guild_role not in user.roles:
                            await user.add_roles(guild_role)
                        break
                break


@client.event
async def on_raw_reaction_remove(payload: RawReactionActionEvent):
    """Function called on user removing a reaction from a message"""
    role_data = get_config('channels')
    messagelink = f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}"
    if "Role Bot" in role_data and messagelink in role_data["Role Bot"]:
        emoji = str(payload.emoji)  # payload.emoji.id if payload.emoji.is_custom_emoji() else str(payload.emoji)
        for role in role_data["Role Bot"][messagelink]["Roles"]:
            # added or statement for backward compatibility
            if role["Role Emote"] == emoji or (
                    payload.emoji.is_custom_emoji() and payload.emoji.id == role["Role Emote"]):
                guild = await client.fetch_guild(payload.guild_id)
                user = await guild.fetch_member(payload.user_id)
                for guild_role in guild.roles:
                    if guild_role.id == role["Role ID"]:
                        if guild_role in user.roles:
                            await user.remove_roles(guild_role)
                        break
                break


@client.event
async def on_voice_state_update(member: Member, before: VoiceState, after: VoiceState):
    """Function called on all user voice state updates"""
    # if the user channel has not changed
    if before.channel != after.channel:
        for channel in (before.channel, after.channel):
            await edit_voice_status(channel)


######################################################################################################################
# Commands and error catchers
######################################################################################################################
@app_commands.check(approved_channel_user)
@client.tree.command(name="addchannel", description='Add channel to channels the bot is allowed to update.')
@app_commands.describe(channel="#channelname that the bot is allowed to edit")
async def addchannel(interaction: discord.Interaction, channel: VoiceChannel):
    config_channels = get_config('channels')
    # if the channel is already whitelisted
    if channel.id in config_channels["Channels"].values():
        await interaction.response.send_message(f'The channel {channel.mention} is already whitelisted',
                                                ephemeral=True)

    else:
        config_channels["Channels"][channel.name] = channel.id
        save_config('channels', config_channels)
        await edit_voice_status(channel)
        await interaction.response.send_message(f'The channel {channel.mention} has been whitelisted', ephemeral=True)


# @addchannel.error
# async def addchannel_error(interaction: discord.Interaction, error: app_commands.errors):
#     pass


@app_commands.check(approved_channel_user)
@client.tree.command(name="removechannel", description='Remove channel from channels the bot is allowed to update.')
@app_commands.describe(channel="#channelname that the bot is not allowed to edit")
async def removechannel(interaction: discord.Interaction, channel: VoiceChannel):
    if channel in interaction.guild.channels:
        config_channels = get_config('channels')
        icon = get_config(f'configs-{interaction.guild_id}')["Active Icon"]

        # if the channel is already whitelisted
        if channel.id not in config_channels["Channels"].values():
            await interaction.response.send_message(f'The channel {channel.mention} is already not whitelisted',
                                                    ephemeral=True)
        else:
            for config_channel in config_channels["Channels"]:
                if config_channels["Channels"][config_channel] == channel.id:
                    del config_channels["Channels"][config_channel]
                    break
            save_config('channels', config_channels)
            await interaction.response.send_message(
                f'The channel {channel.mention} has been removed from the whitelist', ephemeral=True)

        if channel.name.endswith(icon):
            await channel.edit(name=channel.name[:len(channel.name) - len(icon)])


@removechannel.error
async def removechannel_error(interaction: discord.Interaction, error: app_commands.errors):
    pass


@app_commands.check(approved_role_user)
@client.tree.command(name="addrole", description='Allow for a role to be added to the roles message.')
@app_commands.describe(role="@role you wish to add",
                       emote="The emote you wish to use as the reaction (make sure it's one the bot has too)",
                       messagelink="The link to the message you wish to use (right click and Copy Message Link)"
                       )
async def addrole(interaction: discord.Interaction,
                  role: discord.Role,
                  emote: str,
                  messagelink: str
                  ):
    if role.name == '@everyone':
        await interaction.response.send_message('Last I checked you don\'t need to assign the role @everyone',
                                                ephemeral=True)
        return

    # extract channel and message ids as ints from the link
    channelid, messageid = [int(x) for x in messagelink.split('/')[-2:]]

    channel = await interaction.guild.fetch_channel(channelid)
    message = await channel.fetch_message(messageid)

    # if the emote is a custom emote, get it
    # if '<' in emote:
    #     emote = await interaction.guild.fetch_emoji(int((emote.split(':')[-1])[:-1]))  # obtain emote
    # if it is a custom emote, get the id. Otherwise, use the default emote
    emote_id = emote  # emote.id if hasattr(emote, "id") else emote

    # gets config info, will need everything even though we're only changing Role Bot
    role_config = get_config('channels')

    # list of roles
    stored_roles = []

    # check through existing message in stored configs
    if "Role Bot" in role_config:
        if messagelink in role_config["Role Bot"]:
            stored_roles = role_config["Role Bot"][messagelink]["Roles"]

        # this would only be true if previously exists
        if stored_roles and message:
            for r_pos, r in enumerate(stored_roles):
                # if the role already existed
                if r["Role ID"] == role.id:

                    # if the new emote is not the old emote, replace it
                    old_emote = r["Role Emote"]
                    if old_emote != emote_id:
                        # if it is just an ID, then get the associated emote
                        if isinstance(old_emote, int):
                            old_emote = await interaction.guild.fetch_emoji(int((emote.split(':')[-1])[:-1]))

                        # remove the old reaction and add the new one
                        await interaction.response.send_message(
                            f'The role icon for {role.mention} has been replaced from {old_emote} to {emote}'
                            f'\n{messagelink}', ephemeral=True)
                        await message.remove_reaction(old_emote, client.user)
                        await message.add_reaction(emote)
                        role_config["Role Bot"][messagelink]["Roles"] = [
                            *role_config["Role Bot"][messagelink]["Roles"][:r_pos],
                            *role_config["Role Bot"][messagelink]["Roles"][r_pos + 1:],
                            {"Role Name": role.name, "Role ID": role.id, "Role Emote": emote_id}]
                        save_config('channels', role_config)
                        return
                    # otherwise, nothing has changed
                    else:
                        await interaction.response.send_message(f'The role icon for {role.mention} is already {emote}'
                                                                f'\n{messagelink}', ephemeral=True)
                    return
                # if the emote is found somewhere else
                elif r["Role Emote"] == emote_id:
                    # if it doesn't exist already, then let's make it exist
                    await interaction.response.send_message(
                        f'The emote {emote} has already been used for the role {role.mention}'
                        f'\n{messagelink}', ephemeral=True)
                    return

            # if it doesn't exist already, then let's make it exist
            await message.add_reaction(emote)
            await interaction.response.send_message(f'The role {role.mention} has added and given the emote: {emote}'
                                                    f'\n{messagelink}', ephemeral=True)
            if 'Roles' in role_config["Role Bot"][messagelink] and isinstance(
                    role_config["Role Bot"][messagelink]["Roles"], list):
                role_config["Role Bot"][messagelink]["Roles"].append({"Role Name": role.name,
                                                                      "Role ID": role.id,
                                                                      "Role Emote": emote_id})
            else:
                role_config["Role Bot"][messagelink]["Roles"] = [{"Role Name": role.name,
                                                                  "Role ID": role.id,
                                                                  "Role Emote": emote_id}]
            save_config('channels', role_config)
            return

    # if a channel was provided, find message and generate data
    if message:
        role_data = {
            "Roles": [{"Role Name": role.name, "Role ID": role.id, "Role Emote": emote_id}]
        }
        role_config["Role Bot"][messagelink] = role_data
        await message.add_reaction(emote)
        save_config('channels', role_config)

        # the bot will then react to the message
        await interaction.response.send_message(
            f'The reaction message has been stored and the role {role.mention} can be obtained by reacting with {emote}'
            f'\n{messagelink}', ephemeral=True)


@addrole.error
async def addrole_error(interaction: discord.Interaction, error: app_commands.errors):
    if isinstance(error, TransformerError):
        await interaction.response.send_message('Message was not found in the given channel.', ephemeral=True)
    if isinstance(error, HTTPException):
        if error.code == 400:
            await interaction.response.send_message('Invalid emoji used', ephemeral=True)
    pass


@app_commands.check(approved_role_user)
@client.tree.command(name="removerole", description='Remove a role from the roles message.')
@app_commands.describe(role="@role you wish to remove",
                       messagelink="The link to the message you wish to use (right click and Copy Message Link)"
                       )
async def removerole(interaction: discord.Interaction,
                     role: discord.Role,
                     messagelink: str
                     ):
    # extract channel and message ids as ints from the link
    channelid, messageid = [int(x) for x in messagelink.split('/')[-2:]]

    channel = await interaction.guild.fetch_channel(channelid)
    message = await channel.fetch_message(messageid)

    # gets config info, will need everything even though we're only changing Role Bot
    role_config = get_config('channels')

    # list of roles
    stored_roles = []

    # check through existing message in stored configs
    if "Role Bot" in role_config:
        if messagelink in role_config["Role Bot"]:
            stored_roles = role_config["Role Bot"][messagelink]["Roles"]

        # this would only be true if previously exists
        if stored_roles and message:
            for r_pos, r in enumerate(stored_roles):
                # if the role already existed
                if r["Role ID"] == role.id:

                    # if the new emote is not the old emote, replace it
                    emote = r["Role Emote"]
                    if isinstance(emote, int):
                        emote = await interaction.guild.fetch_emoji(emote)
                    # remove the old reaction and add the new one
                    await interaction.response.send_message(
                        f'The role icon for {role.mention} with emote {emote} has been removed from the message'
                        f'\n{messagelink}', ephemeral=True)
                    await message.remove_reaction(emote, client.user)
                    del role_config["Role Bot"][messagelink]["Roles"][r_pos]
                    if not role_config["Role Bot"][messagelink]["Roles"]:
                        del role_config["Role Bot"][messagelink]
                    save_config('channels', role_config)
                    return

        # if it was not found
        await interaction.response.send_message(
            f'The reaction message does not seem to have a reaction role for {role.mention}\n{messagelink}',
            ephemeral=True)
        return
    # if it was not found
    await interaction.response.send_message(
        f'The message you are looking for does not seem to have any reaction roles associated with it', ephemeral=True)


@removerole.error
async def removerole_error(interaction: discord.Interaction, error: app_commands.errors):
    pass


@app_commands.check(approved_role_user)
@client.tree.command(name="bulkaddroles", description='Add multiple roles to a message.')
@app_commands.describe(roles="@roles you wish to add",
                       emotes="Emotes you wish to use per role in the correct order (separate with spaces)",
                       messagelink="The link to the message you wish to use (right click and Copy Message Link)"
                       )
async def bulkaddroles(interaction: discord.Interaction,
                       roles: str,
                       emotes: str,
                       messagelink: str
                       ):
    old_config_data = get_config('channels')

    roles = roles.replace('>', '').replace(',', '')
    roles = ''.join(roles.split())
    roles = [int(i) for i in roles.split('<@&')[1:]]
    emotes = emotes.split()
    if len(roles) != len(emotes):
        await interaction.response.send_message(f'{len(roles)} roles but {len(emotes)} emotes detected.\n'
                                                f'Ensure emotes are separated via spaces and try again', ephemeral=True)
        return
    await interaction.response.defer()
    message = {'Roles': []}

    all_roles = await interaction.guild.fetch_roles()
    all_role_ids = [r.id for r in all_roles]
    all_role_names = [r.name for r in all_roles]

    pairings = ''
    for i, role in enumerate(roles):
        if role not in all_role_ids:
            await interaction.followup.send(f'Role: <@&{role}> not found', ephemeral=True)
            return
        else:
            index = all_role_ids.index(role)
            message['Roles'].append({"Role Name": all_role_names[index], "Role ID": role, "Role Emote": emotes[i]})
            pairings += f'- {emotes[i]} <@&{role}>\n'

    config_data = get_config('channels')
    config_data['Role Bot'][messagelink] = message
    save_config('channels', config_data)
    if await reloadrolesmessage(interaction, messagelink, False):
        await interaction.followup.send(f'{messagelink} has had the following roles added to it:\n{pairings}',
                                        ephemeral=True)
        return

    save_config('channels', old_config_data)
    await interaction.followup.send(f'An error occurred replacing the emotes. '
                                    f'Are the emotes from servers the bot is also present in?',
                                    ephemeral=True)


@client.tree.command(name="getroles", description='Shows roles associated with a message.')
@app_commands.describe(messagelink="The link to the message you wish to inspect (right click and Copy Message Link)")
async def getroles(interaction: discord.Interaction,
                   messagelink: str):
    config_data = get_config('channels')
    if messagelink not in config_data['Role Bot'] or not config_data['Role Bot'][messagelink]:
        await interaction.response.send_message('There does not appear to be any data associated with this message',
                                                ephemeral=True)
        return
    message = '# Roles:\n'
    for role in config_data['Role Bot'][messagelink]['Roles']:
        message += f'- {role['Role Emote']} <@&{role['Role ID']}>\n'
    await interaction.response.send_message(message + messagelink, ephemeral=True)


@app_commands.check(approved_role_user)
@client.tree.command(name="generateroles", description='A quick role creation command.')
@app_commands.describe(roles="Role names list. Separate each role with a \",.\"",
                       colour="R,G,B values or #hex value for the roles (Default = None)")
async def generateroles(interaction: discord.Interaction, roles: str, colour: str = None):
    roles = roles.split(',.')

    if colour and ',' in colour:
        colour = [int(i) for i in (''.join(colour.split())).split(',')]
        if len(colour) != 3:
            colour = None
        else:
            try:
                colour = Colour.from_rgb(*colour)
            # broad exception used as None is a failsafe
            except Exception:
                colour = None
    elif colour:
        try:
            colour = colour.replace('#', '')
            colour = Colour.from_str('#' + colour)
        # broad exception used as None is a failsafe
        except Exception:
            colour = None
    message = '## Generated the following roles:\n'
    for r in roles:
        if colour:
            role = await interaction.guild.create_role(name=r, colour=colour)
        else:
            role = await interaction.guild.create_role(name=r)
        message += f'- {role.mention}\n'
    await interaction.response.send_message(message, ephemeral=True)


@app_commands.check(approved_role_user)
@client.tree.command(name="checkupdate", description='Compare the bot to the latest version available.')
async def checkupdate(interaction: discord.Interaction):
    git_version = check_version()
    if git_version != __VERSION__:
        await interaction.response.send_message(f'# Update Found\n'
                                                f'Current version: `{__VERSION__}`\n'
                                                f'Version available: `{git_version}`\n'
                                                f'The latest version has been downloaded.\n'
                                                f'Please install the latest instance available', ephemeral=True)
    else:
        await interaction.response.send_message(f'Current version: `{__VERSION__}` is up to date', ephemeral=True)


if __name__ == '__main__':
    setup(client)
