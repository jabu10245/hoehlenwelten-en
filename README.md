# Höhlenwelten - Der leuchtende Kristall


** Disclaimer: ** It turns out there is a lot more text that can't be translated with this method. Unless I figure out a way to extract them, this projectt is useless.


This project patches the executable `HW.EXE` in the German game Höhlenweiten with translations into English.

For running the patch, execute the commands below. Before running those commands, you have to have the game installed somewhere.

```[sh]
# Download the project files and copy over the executable.
git clone https://github.com/jabu10245/hoehlenwelten-en.git
cd hoehlenwelten-en
cp <path-to-game-folder>/HW.EXE ./

# Optionally, edit the "strings.txt" file to add translations. I'm going to use vim here:
vim strings.txt

# Patch executable, applying the translations.
python3 translate.py

# Copy over the translated executable into the game folder. Maybe make a backup of the original file first.
cp ./HW_EN.EXE <path-to-game-folder>/HW.EXE
```

You can also delete the file `strings.txt` to start with a fresh translation.
