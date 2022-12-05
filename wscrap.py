from multiprocessing import Value, Pool
from time import sleep
from requests import get
from sys import exit as sysex, argv
from os import path
from time import time
from re import compile, findall
from bs4 import BeautifulSoup
from json import dumps

IS_FILE = lambda file : path.exists(file)

def help():
    print(f"Usage: {argv[0]} <options> <target>")
    print("Note: -wl / --wordlist option is mandatory")
    print("Help isn't properly implemented yet since I'm still changing stuff and it's the last task in the list")
    sysex()

def ctrlc(i,f):
    print(f"\n\nUser pressed ctrl+c, exiting...")
    sysex()

class Ps:
    def init_pool(currentUrl,sval,verifyStatus,validCodes,exts):
        global url; global req; global verify; global codes; global extensions
        extensions = exts
        url = currentUrl
        req = sval
        verify = verifyStatus
        codes = validCodes

class Armory:
    def PathBuster0(arr):
        found = []
        for w in arr:
            ans = get(f"{url}{w}",verify=verify)
            req.value+=1
            if ans.status_code in codes:
                found.append((w,ans))
        return found

    def PathBuster1(arr):
        found = []
        for w in arr:
            ans = get(f"{url}{w}",verify=verify)
            req.value+=1
            if ans.status_code in codes:
                found.append((w,ans))
            for ext in extensions:
                ans = get(f"{url}{w}.{ext}")
                req.value+=1
                if ans.status_code in codes:
                    found.append((f"{w}.{ext}",ans))
        return found

class DataParser:
    def parse(rawdata, rules):
        data = []
        if rules:
            for path,ans in rawdata:
                data.append(
                    {
                        'Path':path,
                        'Status':ans.status_code,
                        'Content-Length':ans.headers['Content-length'],
                        'Data extracted':DataParser.extractData(ans.content,rules)
                    }
                )
        else:
            for path,ans in rawdata:
                data.append(
                    {
                        'Path':path,
                        'Status':ans.status_code,
                        'Content-Length':ans.headers['Content-length'],
                    }
                )
        return data

    def extractData(content,rules):
        extracted = []
        for rule in rules:
            extracted.append(findall(compile(rule),BeautifulSoup(content,'html.parser').text))
        return extracted
    
    def printJson(data):
        print(dumps(data,indent=4))

class ArgumentParser():
    def __init__(self):
        if len(argv) == 1:help()
        self.targets = '' # file | string | csv  [!]MANDATORY OPTION[!]
        self.wordlist = '' # file [!]MANDATORY OPTION[!]
        self.processes = 2 # int - amount of processes to spawn to achieve the task
        self.port = 80 # int
        self.validStatusCodes = (200,301) # int | csv
        self.rules = '' # file | string | csv - will be stored in a tuple
        self.extensions = '' # csv
        self.protocol = 'http' # http | https - varies with -ssl option
        self.verify = True # shared variable which indicates if we should verify host, required when doing https requests

        n = 0; args = argv[1:]
        while n < len(args):
            match args[n]:
                case "-h" | "--help":
                    help();n+=1
                case "-t" | "--target":
                    self.targets = args[n+1];n+=2
                case "-p" | "--port":
                    self.port= args[n+1];n+=2
                case "-wl" | "--wordlist":
                    self.wordlist = args[n+1];n+=2
                case "-ps" | "--processes":
                    self.processes = args[n+1];n+=2
                case "-ext" | "--extensions":
                    self.extensions = tuple(args[n+1].split(','));n+=2
                case "-r" | "--rules":
                    self.rules = args[n+1];n+=2
                case "-sc" | "--status-codes":
                    self.validStatusCodes = tuple(args[n+1].split(','));n+=2
                case "-ssl" | "--ssl":
                    self.verify = False
                    self.protocol = 'https'
                    n+=1
                case _:
                    print(f"Option '{args[n]}' doesn't exist")
                    sysex()

        # Targets option is mandatory
        if not self.targets:
            print("[+] Target/s must be supplied")
            sysex()

        # Wordlist option is mandatory
        if not self.wordlist:
            print("[+] Wordlist must be supplied")
            sysex()
        
        if not IS_FILE(self.wordlist):
            print(f"[+] Wordlist {self.wordlist} doesn't exist")
            sysex()

        if IS_FILE(self.rules):
            self.rules = tuple(open(self.rules).read().split())
        else:
            self.rules = self.rules.split(',') if self.rules else ""

        try:
            self.port = int(self.port)
            self.processes = int(self.processes)
        except ValueError as err:
            print(f"[+] Port and processes amount must be integers: {err}")
            sysex()

        if IS_FILE(self.targets):
            self.targets = tuple(open(self.targets).read().split())
        else:
            self.targets = tuple(self.targets.split(','))

class Wscrapper(ArgumentParser):
    def __init__(self):
        super().__init__()
        self.currentUrl = ""
        self.sval = Value('i',0)
        self.data = []

        self.__setWordlist()
        self.__setMode()
        self.spawn()

    def __setMode(self):
        self.mode = Armory.PathBuster1 if self.extensions else Armory.PathBuster0

    def __setWordlist(self):
        self.splittedWordlist = [] # INITIALIZATION
        arr = tuple(open(self.wordlist).read().split())
        fileLines = len(arr)
        self.maxReqs = len(self.targets)*(fileLines+(fileLines*len(self.extensions))) # INITIALIZATION
        begL = 0
        wpp = int(fileLines/self.processes)

        for i in range(self.processes-1):
            self.splittedWordlist.append(arr[begL:begL+wpp])
            begL+=wpp
        
        if self.processes > 1:
            self.splittedWordlist.append(arr[begL:])

    def spawn(self):
        print(f"Spawning {self.processes} processes")
        for target in self.targets:
            self.currentUrl = f"{self.protocol}://{target}:{self.port}/"
            print(f"Targetting {target}")
            
            p = Pool(initializer=Ps.init_pool,initargs=(self.currentUrl,self.sval,self.verify,self.validStatusCodes,self.extensions))
            r = p.map_async(self.mode,self.splittedWordlist)
            
            while not r.ready():
                print(f"Requests: {self.sval.value}/{self.maxReqs}",end='\r')
                sleep(1)
            print(f"Requests: {self.sval.value}/{self.maxReqs}")

            data = []
            for i in r.get():
                for ans in i:
                    data.append(ans)

            self.data.append((target,DataParser.parse(data,self.rules)))
        DataParser.printJson(self.data)

def main():
    b = time()
    Wscrapper()
    e = time()
    print(f"Time: {round(e-b,6)}s")

if __name__ == "__main__":
    main()
