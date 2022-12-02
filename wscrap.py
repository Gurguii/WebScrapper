import signal
from os import path
from requests import get
from re import compile, findall
from threading import Thread, Event
from bs4 import BeautifulSoup
from time import sleep
from json import dumps
from urllib3 import disable_warnings
from sys import exit as sysex, argv

STOP_THREADS_EVENT = Event()
ISFILE = lambda file : path.exists(file)

def ctrlC(i,f):
    print("\n\nUser pressed ctrl+c ...")
    ws.printInfo()
    STOP_THREADS_EVENT.set()
    sysex()

def help():
    print(f"Usage: {argv[0]} <options> <target>")
    print("Note: -wl / --wordlist option is mandatory")
    sysex()

class ArgumentParser():
    def __init__(self):
        if len(argv) == 1:help()
        self.targets = '' # file | string | csv  [!]MANDATORY OPTION[!]
        self.wordlist = '' # file [!]MANDATORY OPTION[!]
        self.threadC = 10 # int
        self.port = 80 # int
        self.validStatusCodes = (200,301) # int | csv
        self.rules = '' # file - will be stored in a tuple
        self.extensions = '' # csv
        self.protocol = 'http' # http | https - varies with -ssl option
        n = 0; args = argv[1:]
        while n < len(args):
            match args[n]:
                case "-h" | "--help":
                    help();n+=1
                case "-target" | "--target":
                    self.targets = args[n+1];n+=2
                case "-p" | "--port":
                    self.port= args[n+1];n+=2
                case "-wl" | "--wordlist":
                    self.wordlist = args[n+1];n+=2
                case "-t" | "--threads":
                    self.threadC = args[n+1];n+=2
                case "-ext" | "--extensions":
                    self.extensions = tuple(args[n+1].split(','));n+=2
                case "-r" | "--rules":
                    self.rules = args[n+1];n+=2
                case "-sc" | "--status-codes":
                    self.validStatusCodes = tuple(args[n+1].split(','));n+=2
                case "-ssl" | "--ssl":
                    disable_warnings()
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
        
        if not ISFILE(self.wordlist):
            print(f"[+] Wordlist {self.wordlist} doesn't exist")
            sysex()

        if ISFILE(self.rules):
            self.rules = tuple(open(self.rules).read().split())
        else:
            self.rules = self.rules.split(',') if ',' in self.rules else ()
        try:
            self.port = int(self.port)
            self.threadC = int(self.threadC)
        except ValueError as err:
            print(f"[+] Port and thread amount must be integers => {err}")
            sysex()

        if ISFILE(self.targets):
            self.targets = tuple(open(self.targets).read().split())
        else:
            self.targets = tuple(self.targets.split(','))

class WebScrapper(ArgumentParser):
    def __init__(self):
        super().__init__()
        self.currentTarget = ''
        self.dataExtracted = []
        self.finishedThreads = 0
        self.requestsMade = 0
        self.__setPathBuster(len(self.extensions),len(self.rules))

    # the 1/0 means EXTENSIONS | RULES
    # 11 means user inputted extensions and rules // 00 means user didn't input extra extensions or rules etc. 
    # I did this to try and achieve the best performance since each
    # function does only what it needs to and doesn't waste time doing 
    # dumb checks(except the STOP_THREADS_EVENT hehe)
    def __setPathBuster(self,ext,rul):
        if ext and rul:
            self.mode = self.pathBuster11
        elif ext and not rul:
            self.mode = self.pathBuster10
        elif not ext and rul:
            self.mode = self.pathBuster01
        elif not ext and not rul:
            self.mode = self.pathBuster00

    def pathBuster11(self,arr):
        for w in arr:
            if STOP_THREADS_EVENT.is_set(): return
            ans = get(f"{self.url}{w}",verify=False)
            self.requestsMade+=1
            if ans.status_code in self.validStatusCodes:
                self.extractData(w,ans)
            for ext in self.extensions:
                ans = get(f"{self.url}{w}.{ext}",verify=False)
                self.requestsMade+=1
                if ans.status_code in self.validStatusCodes:
                    self.extractData(f"{w}.{ext}",ans)
        self.finishedThreads+=1

    def pathBuster00(self,arr):
        for w in arr:
            if STOP_THREADS_EVENT.is_set(): return
            ans = get(f"{self.url}{w}",verify=False)
            self.requestsMade+=1
            if ans.status_code in self.validStatusCodes:
                self.addFoundDir(w,ans)
            for ext in self.extensions:
                ans = get(f"{self.url}{w}.{ext}")
                self.requestsMade+=1
                if ans.status_code in self.validStatusCodes:
                    self.addFoundDir(f"{w}.{ext}",ans)
        self.finishedThreads+=1

    def pathBuster01(self,arr):
        for w in arr:
            if STOP_THREADS_EVENT.is_set(): return
            ans = get(f"{self.url}{w}",verify=False)
            if ans.status_code in self.validStatusCodes:
                self.extractData(w,ans)
            self.requestsMade+=1
        self.finishedThreads+=1

    def pathBuster10(self,arr):
        for w in arr:
            if STOP_THREADS_EVENT.is_set(): return
            ans = get(f"{self.url}{w}",verify=False)
            self.requestsMade+=1
            if ans.status_code in self.validStatusCodes:
                self.addFoundDir(w,ans)
            for ext in self.extensions:
                ans = get(f"{self.url}{w}.{ext}")
                self.requestsMade+=1
                if ans.status_code == 200:
                    self.extractData(w,ans)
        # Thread ended
        self.finishedThreads+=1

    def addFoundDir(self,path,ans):
        self.currentTarget['found routes'].append({'name':path,'status':ans.status_code,'Content type':ans.headers['Content-type'],'Length':ans.headers['Content-Length']})
    
    def extractData(self,path,ans):
        data = []
        for rule in self.rules:
            matches = findall(compile(rule),BeautifulSoup(ans.content,'html.parser').text)
            if matches:
                data.append((rule," ".join(matches)))
        if data:
            self.currentTarget['found routes'].append({'name':path,'status':ans.status_code,'Content type':ans.headers['Content-type'],'Length':ans.headers['Content-Length'],'Data extracted':data})
        else:
            self.currentTarget['found routes'].append({'name':path,'status':ans.status_code,'Content type':ans.headers['Content-type'],'Length':ans.headers['Content-Length']})

    def printInfo(self):
        print("\n"+dumps(self.dataExtracted, sort_keys=False, indent=4))

    def runThreads(self):
        wlArray = tuple(open(self.wordlist).read().split())
        fileLines = len(wlArray)
        total_requests = len(self.targets)*(fileLines+(fileLines*len(self.extensions))) 

        print(f"[+] - Starting with {self.threadC} threads")

        for t in self.targets:
            print(f"[+] - Current target => {t}")

            self.url = f"{self.protocol}://{t}:{self.port}/"; self.finishedThreads = 0; self.currentTarget = {'target':t,'found routes':[]};
            wpt = int(fileLines/self.threadC); begL = 0; mythreads = []

            for i in range(self.threadC-1):
                mythreads.append(Thread(target=self.mode,args=(wlArray[begL:begL+wpt],)))
                begL+=wpt
            mythreads.append(Thread(target=self.mode,args=(wlArray[begL:],)))

            for th in mythreads:
                th.start()

            # Keep main thread sleeping until others end or ctrl+c
            # is pressed, in that case the STOP_THREADS_EVENT will
            # be set and threads will terminate their execution(line 91)
            while not STOP_THREADS_EVENT.is_set() and self.finishedThreads != self.threadC:
                print(f"Requests: {self.requestsMade}/{total_requests}",end='\r')
                sleep(1)

            # After threads finish, before moving onto the next target, append currentTarget object to dataExtracted
            self.dataExtracted.append(self.currentTarget)
            continue
        print(f"Requests: {self.requestsMade}/{total_requests}")

# ctrl+c signal handler
signal.signal(signal.SIGINT,ctrlC)
# Create an WebScrapper instance that will parse arguments
ws = WebScrapper()
# Start threads
ws.runThreads()
# Print extracted data
ws.printInfo()
