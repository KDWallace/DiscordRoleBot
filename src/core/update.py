import asyncio
import os

import discord
import requests
from github import Github

# for checking version
__VERSION__ = "1.1"

import src.core.core as core
from src.core.util import logger


def check_version() -> str | None:
    """Function for checking on github for the most recent version of the discord bot
    Returns string of latest github version, or None if not available"""
    logger('Checking for updates...', end='')
    src_url = 'https://github.com/KDWallace/DiscordRoleBot/blob/main/src/core/update.py'
    r = requests.get(src_url)

    # if everything is all good
    if r.status_code == 200:
        text = r.text
        if "__VERSION__ = " in text:
            git_version = text.split('__VERSION__ = ')[1].replace('\\', '').split('"')[1]
            if git_version == __VERSION__:
                print(f"Up to date (Latest version: {git_version})")
            else:
                print(f"An update is available (Current version: {__VERSION__}, Latest Github Version: {git_version})")
                logger(f"Downloading update to: \"{core.PATH}version {git_version}\"...", end='')
                update_from_github(git_version)
            return git_version


def update_from_github(version: str | None):
    """Downloads the contents of the repo for this bot and places it inside a given directory"""
    # using pygithub library
    # initialise object for requests
    with Github() as g:

        # project info for the repo
        username = 'KDWallace'
        repo_name = 'DiscordRoleBot'

        # request info
        user = g.get_user(username)
        repo = user.get_repo(repo_name)

        if repo:
            directory = f'{core.PATH}version {version}'

            # create directory for new version
            if not os.path.isdir(directory):
                os.mkdir(directory)

                # get all contents of the repo as an array
                contents = repo.get_contents('')

                # while there are objects within the array
                while contents:
                    # allocate and remove the first object in the array
                    file_content = contents.pop(0)
                    # if it is a directory, create the relevant directory if needed and add back into contents
                    if file_content.type == "dir":
                        contents.extend(repo.get_contents(file_content.path))
                        current_dir = os.path.join(directory, file_content.path)
                        if not os.path.exists(current_dir):
                            os.mkdir(current_dir)
                    # if it is a file, create file with relevant binary data
                    else:
                        filename = os.path.join(directory, file_content.path)
                        if os.path.isfile(filename):
                            os.rename(filename, filename + '.old')
                        with open(filename, "wb") as f:
                            f.write(file_content.decoded_content)
                print('Download complete')
            else:
                print(f'Update already downloaded.\nPlease use the package found in:\n\t{directory}')

        else:
            print('Was unable to find: https://github.com/KDWallace/DiscordRoleBot/')


async def update_routine(client):
    while True:
        git_version = check_version()
        if git_version != __VERSION__:
            await client.change_presence(status=discord.Status.dnd,
                                         activity=discord.Activity(type=discord.ActivityType.custom,
                                                                   name="custom",
                                                                   state=f"Outdated. V{git_version} is available"))

        else:
            await client.change_presence(status=discord.Status.online,
                                         activity=discord.Activity(type=discord.ActivityType.custom,
                                                                   name="custom",
                                                                   state=f"Current version: V{__VERSION__}"))
        # sleep for a day
        await asyncio.sleep(86400)
