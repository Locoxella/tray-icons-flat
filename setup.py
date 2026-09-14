from setuptools import setup, find_packages

setup(
    name="tray-icons-flat",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Pillow",
        "numpy",
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "tray-icons-flat = tray_icons_flat.cli:main",
        ],
    },
)
