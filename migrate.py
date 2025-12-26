import os
from dotenv import load_dotenv
from src.commands import cli

if __name__ == '__main__':
    # Load environment variables from .env file
    load_dotenv()
    cli()