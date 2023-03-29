# Stash Split Duplicate Merged Files

This is a plugin for Stash App, that will search for scenes that have duplicate files and are merged.
It then itterates over the files skipping the first one and then using the next files to create new scenes

## Use Case

To split merged files, to allow those files to appear in deduplication methods to delete duplicates, more specifically for merged files under once scene that are identicall files.

## Usage

1. Copy repository into Stash plugins folder.
2. In repository folder setup a Python virtual enviorment under .venv and install requirements or edit split.yml and just enter ' - "python"' instead of ' - "/.venv/Scripts/python"'
3. Goto Stash Settings > Plugins, and press Reload Plugins. The plugin will now appear in Settings > Tasks
4. Press Setup Tags, to create an ingore tag, that you can tag scenes that have duplicates but you wish the plugin to ignore
5. Press Split Scenes