from setuptools import setup, find_packages

setup(
    name="detective_bot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot",
        "sqlalchemy",
        "anthropic",
        "python-dotenv",
    ],
)
