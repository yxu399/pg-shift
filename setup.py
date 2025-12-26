from setuptools import setup, find_packages

setup(
    name='pgmigrate',
    version='0.1.0',
    packages=find_packages(), 
    include_package_data=True,
    install_requires=[
        'Click',
        'psycopg2-binary',
        'python-dotenv',
    ],
    entry_points={
        'console_scripts': [
            'pgmigrate = src.main:start', 
        ],
    },
)