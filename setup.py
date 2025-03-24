from setuptools import setup, find_packages

setup(
    name='pathfinder-lfg-bot',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'discord.py',
        'peewee',
        'python-dotenv'
    ],
    entry_points={
        'console_scripts': [
            'lfg-bot=lfg_bot.run:main'
        ]
    },
    author='Knuffle Puffle',
    description='A Discord LFG bot for Pathfinder 2e Westmarch campaigns',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
)


DISCORD_BOT_TOKEN='MTM1Mzc4NjE3NzUwNDk0MDE0Mg.GWxinu.eflUQNWwEeWpYqrs__6-7g8dpbvJISzKy221Q0'

