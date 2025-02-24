#### Module for setup of bot
import os
import sys
from datetime import datetime

from src.core.update import __VERSION__
from src.core.util import logger

# Main path for DIR navigation for files/config
PATH = (os.path.dirname(os.path.realpath(__file__)))[:-8]


def setup(client):
    # checks for all required dirs
    check_dir('config')

    if len(sys.argv) > 1:
        # if so, use the arguments as the name and version
        version = 'Moose\'s Bot: ' + ' '.join(sys.argv[1:])

    # if no arguments were passed (by most likely using an IDE), use this string as the title
    else:
        version = 'Moose\'s Bot version: ' + __VERSION__

    # Basic display
    length = 75 - len(version)
    if length > 0:
        length = int(length / 2)
    else:
        length = 0
    print(('=' * length) + f' {version}' + ('=' * length) + f'\n   - Booted at {datetime.now().strftime("%H:%M:%S")}\n'
                                                            f'   - Please wait...')

    # get bot token
    logger('        Obtaining token from textfile...', end='')
    try:
        # opens file containing bot token
        with open(f'{PATH}/src/TOKEN.txt', 'r') as f:
            TOKEN = f.read()

        # if there is a string in the file, assume found
        if len(TOKEN) > 1:
            print('Token found')

            # attempt to run with this token
            client.run(TOKEN)

        # if file does not contain token, raise exception
        else:
            raise FileNotFoundError()

    # exception thrown if token does not exist or is not valid
    except FileNotFoundError:
        print('\n[ERROR]:  Token not found. Please paste your bot token in the TOKEN.txt file')

    # exception related to bot
    except Exception as e:
        print(e)


def check_dir(*dirs):
    """Function for checking for the existence of necessary directories within the program files.
    Will attempt to generate any that are absent"""
    logger('Checking for required directories:')
    for dir_name in dirs:
        if not os.path.isdir(f'{PATH}/{dir_name}'):
            logger(f'\t - Missing required path: "{PATH}{dir_name}"\nAttempting to create missing path...', end='')
            os.makedirs(f'{PATH}{dir_name}\\')
            print('path created')
        else:
            logger(f'\t - Path "{PATH}{dir_name}" found')


# function if the wrong file is run as the main
def incorrectModuleAsMain():
    logger('This python file should not be used as the main file. Please run "Bot.py" to use this bot')


if __name__ == '__main__':
    incorrectModuleAsMain()
