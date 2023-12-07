"""
Generate language information for translations
"""

import os
import json

Aliases = {
    'AR': ['spanish'], #ar
    'CA': ['catalan'],
    'CH': ['chinese (traditional)'],
    'CN': ['chinese (simplified)'],
    'CS': ['czech'],
    'DA': ['danish'],
    'DE': ['german'],
    'EN': ['english'],
    'ES': ['spanish'],
    'FI': ['finnish'],
    'FR': ['french'],
    'HU': ['hungarian'],
    'ID': ['indonesian'],
    'IT': ['italian'],
    'JP': ['japanese'],
    'KO': ['korean'],
    'NL': ['dutch'],
    'NO': ['norwegian'],
    'PH': ['tagalog','filipino'],
    'PL': ['polish'],
    'PT': ['portuguese'],
    'PTBR': ['portuguese'], #br
    'RO': ['romanian'],
    'RU': ['russian'],
    'TH': ['thai'],
    'TR': ['turkish'],
    'UA': ['ukrainian'],
}

def getTranslateDir():
    from configparser import ConfigParser
    config = ConfigParser()
    config.read("config.ini")
    return config["Directories"]["PZTranslateDir"]

def getTranslateCodes(name):
    if name == "google":
        from deep_translator import GoogleTranslator
        return GoogleTranslator().get_supported_languages(True)

# uses scriptblock - need improvement
def readLanguageFile(filePath: str):
    try:
        with open(filePath,"r") as f:
            d = {}
            for line in f:
                for it in line.split(","):
                    if "=" in it:
                        key, value = it.split("=",1)
                        key = key.strip()
                        value = value.strip()
                        d[key] = value
            # print(d)
            if all(x in d for x in ["text", "charset"]) and d["VERSION"] == "1":
                return d
            else:
                return None
    except:
        return None

# FIXME: Catalan has encoding issues - switch to Cp1252?
def generateLanguagesInfo():
    translateDir = getTranslateDir()
    translateCodes = getTranslateCodes("google")
    all = {}
    with os.scandir(translateDir) as tDir:
        for each in tDir:
            if each.is_dir():
                d = readLanguageFile(os.path.join(translateDir,each.name,"language.txt"))
                if not d:
                    continue
                d["id"] = each.name
                d["tr_code"] = next((translateCodes[x] for x in Aliases[each.name] if x in translateCodes) , None)
                if not d["tr_code"]:
                    print("no tr_code found for",each.name,d["text"])
                    d["tr_code"] = "en"
                all[each.name] = dict(sorted(d.items()))
                # print("'"+ each.name + "': ['" + d["text"].lower() + "'],")
                # print("| " + each.name + " | " + d["text"] + " | " + d["charset"] + " |")
    return all

def getLanguages(generate: bool = False) -> dict[str, dict]:
    LanguagesPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LanguagesInfo.json")
    if generate or not os.path.isfile(LanguagesPath):
        d = generateLanguagesInfo()
        with open(LanguagesPath,"w",encoding="utf-8") as f:
            json.dump(d,f,indent=2)
        return d
    else:
        with open(LanguagesPath,"r",encoding="utf-8") as f:
            return json.load(f)
