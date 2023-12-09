# pz-translate-zx

Project Zomboid translations automation scripts, initialise translations with automatic translations.

Requires:
- Python 
- deep_translator package

How to use:
- Create config.ini from config-template, set the directory for the "Translate" directory you want to translate
- run pz_translate.py from it's directory

## Text Translator

Deep translator supports different translators, you can find more information at: [https://pypi.org/project/deep-translator/](https://pypi.org/project/deep-translator/)

## How to use

The script can be used from the translation folder, or the mod folder, or the project folder with pzstudio structure.

### execute the pz_translate.py file

You can run the script directly, without any arguments and it will translate the folder set in the `config.ini`.

### command line

example for windows
```
py "path_to_script/pz_translate.py" "path to mod folder"
```

### VSCode task

You can add a task like this to run the script. Replace `${path_to_script}/pz_translate.py` with the path to the script. This will target the workspaceFolder for translation.
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Translate Project",
      "type": "shell",
      "command": "py",
      "args": [ "${path_to_script}/pz_translate.py", "${workspaceFolder}" ],
      "group": "none",
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
  ]
}

```
> See https://go.microsoft.com/fwlink/?LinkId=733558 for the documentation about the tasks.json format