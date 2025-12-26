# src/main.py
import os
from dotenv import load_dotenv
from .commands import cli

def start():
    # Load environment variables from .env file
    # We look for .env in the current working directory (where the user runs the command)
    load_dotenv(os.path.join(os.getcwd(), ".env"))
    cli()