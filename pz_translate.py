import os
import pathlib
from shutil import copyfile
import json
from deep_translator import GoogleTranslator
from pz_languages_info import getLanguages

LanguagesDict = getLanguages(False)

FileList = [ "Challenge", "ContextMenu", "DynamicRadio", "EvolvedRecipeName", "Farming", "GameSound", 
            "IG_UI", "ItemName", "Items", "MakeUp", "Moodles", "Moveables", "MultiStageBuild", "Recipes", 
            "Recorded_Media", "Sandbox", "Stash", "SurvivalGuide", "Tooltip", "UI"]

def varsMod(text:str):
    return text.replace("<","<{").replace(">","}>").replace("%1","{%1}")

def varsDemod(text:str):
    return text.replace("{%1}","%1").replace("<{","<").replace("}>",">")

class pz_translator_zx:
    
    def __init__(self,baseDir:str="",source:str="EN",hasConfig:bool=True,gitAtr:bool=False):
        self.baseDir = baseDir
        if hasConfig:
            self.fromConfig(os.path.join(os.path.dirname(__file__),"config.ini"))
        else:
            self.sourceLang = LanguagesDict[source]
        self.translator = GoogleTranslator(self.sourceLang["tr_code"])
        if gitAtr:
            self.checkGitAtributesFile()

    def fromConfig(self,file):
        from configparser import ConfigParser
        config = ConfigParser()
        config.read(file)
        source = config["Translate"]["source"]

        assert os.path.isdir(os.path.join(self.baseDir,source)), "Missing source directory, wrong path?\nDir: " + os.path.join(self.baseDir,source)

        self.baseDir = self.baseDir if self.baseDir else config["Directories"][config["Translate"]["target"]]
        self.sourceLang = LanguagesDict[source]
        if "files" in config["Translate"]:
            self.files = [x for x in [x.strip() for x in config["Translate"]["files"].split(",")] if x in FileList]
        else:
            self.files = FileList
        if "languagesExclude" in config["Translate"]:
            languagesExclude = {x for x in [x.strip() for x in config["Translate"]["languagesExclude"].split(",")] if x in LanguagesDict}
        else:
            languagesExclude = set()
        languagesExclude.add(source)
        if "languagesTranslate" in config["Translate"]:
            languagesTranslate = [x for x in [x.strip() for x in config["Translate"]["languagesTranslate"].split(",")] if x not in languagesExclude and x in LanguagesDict]
        else:
            languagesTranslate = [x for x in LanguagesDict if x not in languagesExclude]
        if "languagesCreate" in config["Translate"]:
            languagesCreate = {x for x in [x.strip() for x in config["Translate"]["languagesCreate"].split(",")] if x in languagesTranslate}
        else:
            languagesCreate = languagesTranslate
        self.translateLanguages = self.getLanguagesForTranslate(languagesTranslate,languagesCreate)

    def getFilePath(self,langId: str, file: str | None = None):
        if not file:
            return os.path.join(self.baseDir, langId)
        else:
            return os.path.join(self.baseDir, langId, file + "_" + langId + ".txt")
        
    def getLanguagesForTranslate(self,translate:list|dict,create:set):
        translateLanguages = []
        for id in translate:
            if os.path.isdir(os.path.join(self.baseDir,id)):
                translateLanguages.append(LanguagesDict[id])
            elif id in create:
                pathlib.Path(self.getFilePath(id)).mkdir()
                translateLanguages.append(LanguagesDict[id])
        return translateLanguages

    def readSourceFile(self,file:str):
        try:
            with open(self.getFilePath(self.sourceLang["id"],file),'r',encoding=self.sourceLang["charset"]) as f:
                lines = []
                tDict = {}
                validLine = False
                key = ""
                text = ""
                
                lines += f.readline().replace("{","{{").replace(self.sourceLang["id"],"{language}")

                for line in f:
                    line = line.replace("{","{{")
                    line = line.replace("}","}}")
                    if "=" in line and "\"" in line:
                        index1 = line.index("=")
                        index2 = line.index("\"",index1+1)
                        index3 = line.rindex("\"")
                        key = line[:index1].strip().replace(".","-")
                        text = line[index2+1:index3]
                        lines += line[:index2+1], "{", key, "}", line[index3:]
                        tDict[key] = text
                        validLine = True
                    elif "--" in line or not line.strip() or line.strip().endswith("..") and not validLine:
                        validLine = False
                        lines += line
                    else:
                        validLine = True
                        lines += line

                    if not validLine or not line.strip().endswith(".."):
                        validLine = False
                        key = ""
                        text = ""

                return "".join(lines), tDict
        except FileNotFoundError:
            return None, None

    def fillTranslationsFromFile(self,lang:dict,file:str,trTexts:dict):
        try:
            with open(self.getFilePath(lang["id"],file),'r',encoding=lang["charset"],errors="replace") as f:
                validLine = False
                key = ""
                text = ""
                
                f.readline()

                for line in f:
                    if "=" in line and "\"" in line:
                        index1 = line.index("=")
                        index2 = line.index("\"",index1+1)
                        index3 = line.rindex("\"")
                        key = line[:index1].strip().replace(".","-")
                        text = line[index2+1:index3]
                        trTexts[key] = text
                        validLine = True
                    elif "--" in line or not line.strip() or line.strip().endswith("..") and not validLine:
                        validLine = False
                    else:
                        validLine = True

                    if not validLine or not line.strip().endswith(".."):
                        validLine = False
                        key = ""
                        text = ""
        except:
            pass
    
    def translate_single(self,tLang,oTexts: dict, tTexts:dict):
        untranslated = len(oTexts) + 1 - len(tTexts)
        if untranslated > 0:
            print(" - Untranslated texts size: ",untranslated)
        for key, value in oTexts.items():
            if key not in tTexts:
                try:
                    tTexts[key] = varsDemod(self.translator.translate(varsMod(value)))
                except:
                    print(" - Failed to translate: " + tTexts["language"] + " | " + value)
                    tTexts[key] = "tr?: " + value

    def translate_batch(self,tLang,oTexts,tTexts):
        keys, values = [],[]
        for key in oTexts:
            if key not in tTexts:
                keys.append(key)
                values.append(varsMod(oTexts[key]))
        if keys:
            try:
                print(" - Untranslated texts size: ",len(values))
                translations = self.translator.translate_batch(values)
                for i,key in enumerate(keys):
                    tTexts[key] = varsDemod(translations[i])
                    try:
                        tTexts[key].encode(tLang["charset"])
                    except:
                        print(" - can not encode: ",key,tTexts[key])
            except:
                for i,k in enumerate(keys):
                    print(" - Failed to translate: " + tTexts["language"] + " | " + values[i])
                    tTexts[k] = "tr?: " + values[i]

    def getTranslations(self,oTexts: dict, tLang: dict, file: str):
        trTexts = {"language":tLang["id"]}
        self.fillTranslationsFromFile(tLang,file,trTexts)
        self.translate_single(tLang,oTexts,trTexts)
        return trTexts

    def writeTranslation(self,lang: dict, file: str, text: str):
        try:
            with open(self.getFilePath(lang["id"],file),"w",encoding=lang["charset"],errors="replace") as f:
                f.write(text)
        except Exception as e:
            print("Failed to write " + lang["id"] + " " + file)
            print(e)
            print(text)

    def translate_self(self):
        for file in self.files:
            templateText, oTexts = self.readSourceFile(file)
            for lang in self.translateLanguages:
                if oTexts:
                    print("Begin Translation Check for: {file}, {id}, {lang} ".format(file=file,id=lang["id"],lang=lang["text"]))
                    self.translator.target = lang["tr_code"]
                    self.writeTranslation(lang,file,templateText.format_map(self.getTranslations(oTexts,lang,file)))
                else:
                    pathlib.Path(self.getFilePath(lang["id"],file)).unlink(missing_ok=True)

    def translate(self,languages:list|dict,files:list,languagesCreate:set[str]|None=set()):
        self.files = files
        self.translateLanguages = self.getLanguagesForTranslate(languages,languagesCreate)
        self.translate_self()

    def convertTranslations(self,readEncodes:dict,languages:list=LanguagesDict,files:list=FileList):
        '''
        attempt to convert to appropriate encoding
        '''
        for id in languages:
            lang = LanguagesDict[id]
            for file in files:
                oFile = self.getFilePath(id,file)
                if os.path.isfile(oFile):
                    f = open(oFile,"r", encoding=readEncodes[id],errors="replace")
                    text = f.read()
                    f.close()

                    f = open(oFile,"w", encoding=lang["charset"],errors="replace")
                    f.write(text)
                    f.close()

    def reencode_self(self):
        '''
        Rewrites existing files, assumes files were using correct encoding. 

        Use when first adding gitattributes file without translating files.
        '''

        self.convertTranslations({ lang["id"] : lang["charset"] for lang in self.translateLanguages},[x["id"] for x in self.translateLanguages],self.files)

    def checkGitAtributesFile(self):
        fPath = os.path.join(self.baseDir,".gitattributes")
        if not os.path.exists(fPath):
            copyfile(os.path.join(os.path.dirname(__file__), ".gitattributes-template.txt"),fPath,follow_symlinks=False)

def translate_project(dir,args):
    with open(os.path.join(dir,"project.json"),"r",encoding="utf-8") as f:
        project = json.load(f)
    for id in project["mods"]:
        if id in project["workshop"]["excludes"]:
            continue
        modpath = pathlib.Path(dir,id,"media","lua","shared","Translate")
        if not modpath.is_dir():
            print("Invalid translation dir:",modpath.resolve())
            continue
        o = pz_translator_zx(modpath.resolve(),gitAtr=True)
        o.translate_self()

def translate_mod(dir,args):
    modpath = pathlib.Path(dir,"media","lua","shared","Translate")
    if modpath.is_dir():
        o = pz_translator_zx(modpath.resolve(),gitAtr=True)
        o.translate_self()
    else:
        print("Invalid translation dir:",modpath.resolve())

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        print("* Translating from config file *")
        pz_translator_zx(gitAtr=True).translate_self()
    elif not os.path.isdir(sys.argv[1]):
        print("Directory does not exist:",sys.argv[1])
    elif os.path.isfile(os.path.join(sys.argv[1],"project.json")):
        print("* Translating project *")
        translate_project(sys.argv[1],sys.argv[2:])
    elif os.path.isfile(os.path.join(sys.argv[1],"mod.info")):
        print("* Translating mod *")
        translate_mod(sys.argv[1],sys.argv[2:])
    else:
        print("* Translating directory *")
        pz_translator_zx(baseDir=sys.argv[1],gitAtr=True).translate_self()
