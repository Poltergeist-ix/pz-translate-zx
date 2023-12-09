
"""

Script to process and fill mod translations for Project Zomboid

Author: Poltergeist

"""

import sys
import pathlib
from shutil import copyfile
import json
from configparser import ConfigParser
from deep_translator import GoogleTranslator
from pz_languages_info import getLanguages

PZ_LANGUAGES = getLanguages()

FILE_LIST = [
    "Challenge", "ContextMenu", "DynamicRadio", "EvolvedRecipeName", "Farming", "GameSound", 
    "IG_UI", "ItemName", "Items", "MakeUp", "Moodles", "Moveables", "MultiStageBuild", "Recipes", 
    "Recorded_Media", "Sandbox", "Stash", "SurvivalGuide", "Tooltip", "UI"
]

def vars_mod(text:str):
    """
    modulate special tags from changing during translation, lazy way.
    Translations require human inspection
    """
    return text.replace("<","<{").replace(">","}>").replace("%1","{%1}")

def vars_demod(text:str):
    "demod special tags"
    return text.replace("{%1}","%1").replace("<{","<").replace("}>",">")

class Translator:
    """
    Translator for a mod's 'Translate' folder 
    """

    def __init__(self, _path: pathlib.Path = None, source: str = "EN", use_config: bool = True,
                 add_gitattributes: bool = True):
        self.path = _path
        self.import_path: pathlib.Path = None
        self.source_lang = PZ_LANGUAGES[source]
        self.languages: list[dict] = []
        self.files: list[str]
        self.pause_on_gitattributes: bool = False
        self.warnings = 0
        self.translator = GoogleTranslator(self.source_lang["tr_code"])
        if use_config:
            self.parse_config()
        if add_gitattributes:
            self.check_gitattributes()

    def parse_config(self):
        """
        Read the config
        """
        config = ConfigParser()
        config.read(pathlib.Path(__file__).resolve().parent / "config.ini")

        if self.path is None:
            self.path = pathlib.Path(config["Directories"][config["Translate"]["target"]])
        source = config["Translate"]["source"]
        source_path = self.path / source

        assert source_path.is_dir(), "Missing source directory: " + source_path.resolve()

        self.source_lang = PZ_LANGUAGES[source]
        if "files" in config["Translate"]:
            self.files = [x for x in [x.strip() for x in config["Translate"]["files"].split(",")] if x in FILE_LIST]
        else:
            self.files = FILE_LIST
        if "languagesExclude" in config["Translate"]:
            lang_exclude = {x for x in [x.strip() for x in config["Translate"]["languagesExclude"].split(",")] if x in PZ_LANGUAGES}
        else:
            lang_exclude = set()
        lang_exclude.add(source)
        if "languagesTranslate" in config["Translate"]:
            lang_translate = [x for x in [x.strip() for x in config["Translate"]["languagesTranslate"].split(",")] if x not in lang_exclude and x in PZ_LANGUAGES]
        else:
            lang_translate = [x for x in PZ_LANGUAGES if x not in lang_exclude]
        if "languagesCreate" in config["Translate"]:
            lang_create = {x for x in [x.strip() for x in config["Translate"]["languagesCreate"].split(",")] if x in lang_translate}
        else:
            lang_create = lang_translate
        self.init_languages(lang_translate,lang_create)

        self.pause_on_gitattributes = config.getboolean("DEFAULT","pause_on_gitattributes",fallback=True)

    def get_path(self, lang_id: str, file: str = None) -> pathlib.Path:
        """
        returns the language directory path, or the file path within
        """
        if file:
            return self.path.joinpath(lang_id, file + "_" + lang_id + ".txt")
        return self.path.joinpath(lang_id)

    def get_import_path(self, lang_id: str, file: str) -> pathlib.Path | None:
        """
        returns the path of the import file or None if there is no import path
        """
        if self.import_path:
            return self.import_path.joinpath(lang_id, file + "_" + lang_id + ".txt")
        return None

    def init_languages(self, translate: list | dict, create: set):
        """
        return final list of languages to translate
        """
        for lang in translate:
            if self.path.joinpath(lang).is_dir():
                self.languages.append(PZ_LANGUAGES[lang])
            elif lang in create:
                self.get_path(lang).mkdir()
                self.languages.append(PZ_LANGUAGES[lang])

    def parse_translation_file(self, lang: dict, texts: dict, file_path: str,
                               create_template: bool = False) -> str | None:
        """
        parse the translation file
        """

        with open(file_path,'r',encoding=lang["charset"]) as f:
            if create_template:
                template = []

            is_valid = False
            key = ""
            text = ""

            line = f.readline()
            if create_template:
                template += line.replace("{","{{").replace(self.source_lang["id"],"{language}")

            for line in f:
                line = line.replace("{","{{")
                line = line.replace("}","}}")
                if "=" in line and "\"" in line:
                    index1 = line.index("=")
                    index2 = line.index("\"",index1+1)
                    index3 = line.rindex("\"")
                    if index2 == index3:
                        self.warn("Missing one \" for: " + line)
                        is_valid = False
                        if create_template:
                            template += line
                    else:
                        is_valid = True
                        key = line[:index1].strip().replace(".","-")
                        text = line[index2+1:index3]
                        texts[key] = text
                        if create_template:
                            template += line[:index2+1], "{", key, "}", line[index3:]
                elif "--" in line or not line.strip() or line.strip().endswith("..") and not is_valid:
                    is_valid = False
                    if create_template:
                        template += line
                else:
                    is_valid = True
                    if create_template:
                        template += line

                if not is_valid or not line.strip().endswith(".."):
                    is_valid = False
                    key = ""
                    text = ""

            if create_template:
                return "".join(template)
            return None

    def translate_single(self, tlang: dict, otexts: dict, trtexts: dict):
        """
        translate missing texts using translators 'translate' function
        """

        untranslated = [x for x in otexts if x not in trtexts]
        if untranslated:
            print(f" - Translating number of texts: {len(untranslated)}")
            self.translator.target = tlang["tr_code"]
            for key in untranslated:
                trtexts[key] = vars_demod(self.translator.translate(vars_mod(otexts[key])))

    def translate_batch(self, trlang: dict, or_texts: dict, tr_texts: dict):
        """
        translate missing texts using translators 'batch translate' function
        """
        keys, values = [],[]
        for key in or_texts:
            if key not in tr_texts:
                keys.append(key)
                values.append(vars_mod(or_texts[key]))
        if values:
            print(" - Untranslated texts size: ",len(values))
            self.translator.target = trlang["tr_code"]
            translations = self.translator.translate_batch(values)
            for i,key in enumerate(keys):
                tr_texts[key] = vars_demod(translations[i])

    def get_translations(self, source_texts: dict, tr_lang: dict, file: str) -> dict:
        """
        return dictionary with translation texts
        """

        tr_map = {"language":tr_lang["id"]}
        fpath = self.get_path(tr_lang["id"],file)
        if fpath.is_file():
            self.parse_translation_file(tr_lang,tr_map,fpath)
        # if there is an import source then parse them on top of current translations
        fpath = self.get_import_path(tr_lang["id"],file)
        if fpath and fpath.is_file():
            self.parse_translation_file(tr_lang,tr_map,fpath)
        self.translate_single(tr_lang,source_texts,tr_map)

        return tr_map

    def write_translation(self, lang: dict, file: str, text: str):
        """
        write the translation file
        """
        try:
            with open(self.get_path(lang["id"],file),"w",encoding=lang["charset"],errors="replace") as f:
                f.write(text)
        except Exception as e:
            print("Failed to write " + lang["id"] + " " + file)
            print(e)
            print(text)

    def translate_main(self):
        """
        translate class instance
        """
        for file in self.files:
            source_file_path = self.get_path(self.source_lang["id"],file)
            if source_file_path.is_file():
                source_map = {}
                template_text = self.parse_translation_file(self.source_lang,source_map,source_file_path,True)
            else:
                source_map = None
            for lang in self.languages:
                if source_map:
                    print(f"Begin Translation Check for: {file}, {lang['id']}, {lang['text']}")
                    self.write_translation(lang,file,template_text.format_map(self.get_translations(source_map,lang,file)))
                else:
                    self.get_path(lang["id"],file).unlink(missing_ok=True)
        print(f"Translation warnings total: {self.warnings}")

    def translate(self, languages: list | dict, files: list, languages_create: set[str]):
        """
        translate without config file
        """
        self.files = files
        self.init_languages(languages,languages_create)
        self.translate_main()

    def reencode_translations(self, read: dict, languages: list = PZ_LANGUAGES, files: list = FILE_LIST):
        '''
        attempt to convert to appropriate encoding
        '''
        for k in languages:
            lang = PZ_LANGUAGES[k]
            for file in files:
                file_path = self.get_path(k,file)
                if file_path.is_file():
                    with open(file_path,"r", encoding=read[k],errors="replace") as f:
                        text = f.read()
                    with open(file_path,"w", encoding=lang["charset"],errors="replace") as f:
                        f.write(text)

    def reencode_initial(self):
        '''
        Rewrites existing files, assumes files were using correct encoding. 

        Use when first adding gitattributes file without translating files.
        '''

        self.reencode_translations(
            { lang["id"] : lang["charset"] for lang in self.languages},
            [x["id"] for x in self.languages],
            self.files
        )

    def check_gitattributes(self):
        """
        add gitattributes file if it doesn't exist
        """
        fpath = self.path / ".gitattributes"
        if not fpath.is_file():
            copyfile(pathlib.Path(__file__).resolve().parent / ".gitattributes-template.txt",fpath.resolve(),follow_symlinks=False)
            if self.pause_on_gitattributes:
                self.reencode_initial()
                input("Added .gitattributes file. Press Enter to continue.\n")

    def warn(self, message: str):
        """print warn message"""
        self.warnings += 1
        print(" - " + message)

def translate_project(project_path):
    """
    translate project
    """

    with open(project_path.joinpath("project.json"),"r",encoding="utf-8") as f:
        project = json.load(f)
    for mod_id in project["mods"]:
        if mod_id in project["workshop"]["excludes"]:
            continue
        modpath = project_path.joinpath(mod_id,"media","lua","shared","Translate")
        if not modpath.is_dir():
            print("Invalid translation dir:",modpath.resolve())
            continue
        o = Translator(modpath,add_gitattributes=True)
        o.translate_main()

def translate_mod(mod_path):
    """
    translate mod
    """

    translate_path = mod_path.joinpath("media","lua","shared","Translate")
    if translate_path.is_dir():
        o = Translator(translate_path,add_gitattributes=True)
        o.translate_main()
    else:
        print("Invalid translation dir:",translate_path.resolve())

if __name__ == '__main__':
    try:
        if len(sys.argv) == 1:
            print("* Translating from config file *")
            Translator().translate_main()
        else:
            _path = pathlib.Path(sys.argv[1])
            if not _path.is_dir():
                print("Directory does not exist:",_path.resolve())
            elif _path.joinpath("project.json").is_file():
                print("* Translating project *")
                translate_project(_path)
            elif _path.joinpath("mod.info").is_file():
                print("* Translating mod *")
                translate_mod(_path)
            else:
                print("* Translating directory *")
                Translator(_path).translate_main()
    except KeyboardInterrupt:
        print("Process manually terminated")
