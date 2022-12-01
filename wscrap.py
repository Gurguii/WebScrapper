import signal
import sys
from os import path
from requests import get
from re import compile, findall
from threading import Thread, Event
from bs4 import BeautifulSoup
from time import sleep
from json import dumps
from urllib3 import disable_warnings

stop_threads_event = Event()
ISFILE = lambda file : path.exists(file)

def ctrlC(i,f):
    print("\n\nUser pressed ctrl+c ...")
    ws.printInfo()
    stop_threads_event.set()
    sys.exit()

def help():
    print(f"Usage: {sys.argv[0]} <options> <target>")
    sys.exit()

class ArgumentParser():
    def __init__(self):
        if len(sys.argv) == 1:help()
        # Set target and default values
        # of options that have'em
        self.targets = sys.argv[-1] # file | string | csv
        self.threadC = 10 # int
        self.port = 80 # int
        self.validStatusCodes = (200,301) # int | csv
        self.wordlist = '' # file
        self.rules = '' # file - will be stored in a tuple
        self.extensions = '' # csv
        self.protocol = 'http' # http | https - varies with -ssl option
        self.url = '' #
        for n in range(1,len(sys.argv)):
            match sys.argv[n]:
                case "-h" | "--help":
                    help()
                case "-p" | "--port":
                    self.port= sys.argv[n+1]
                case "-wl" | "--wordlist":
                    self.wordlist = sys.argv[n+1]
                case "-t" | "--threads":
                    self.threadC = sys.argv[n+1]
                case "-ext" | "--extensions":
                    self.extensions = tuple(sys.argv[n+1].split(','))
                case "-r" | "--rules":
                    self.rules = sys.argv[n+1]
                case "-sc" | "--status-codes":
                    self.validStatusCodes = tuple(sys.argv[n+1].split(','))
                case "-ssl" | "--ssl":
                    disable_warnings()
                    self.protocol = 'https'
                case _:
                    # Default case if no match
                    continue
        # Do some sanitization
        if not self.wordlist:
            print("[+] Wordlist must be supplied")
            sys.exit()
        
        if not ISFILE(self.wordlist):
            print(f"[+] Wordlist {self.wordlist} doesn't exist")
            sys.exit()

        if not ISFILE(self.rules) and self.rules:
            print(f"[+] Rule file {self.rules} doesn't exist")
            sys.exit()

        try:
            self.port = int(self.port)
            self.threadC = int(self.threadC)
        except ValueError as err:
            print(f"[+] Port and thread amount must be integers => {err}")
            sys.exit()

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

    def pathBuster(self, arr):
        if self.extensions and self.rules:
            for w in arr:
                if stop_threads_event.is_set(): return
                ans = get(f"{self.url}{w}",verify=False)
                self.requestsMade+=1

                if ans.status_code in self.validStatusCodes:
                    self.extractData(w,ans)

                for ext in self.extensions:
                    ans = get(f"{self.url}{w}.{ext}",verify=False)
                    self.requestsMade+=1
                    if ans.status_code in self.validStatusCodes:
                        self.extractData(f"{w}.{ext}",ans)
                continue      
        elif self.extensions and not self.rules:
            for w in arr:
                if stop_threads_event.is_set(): return
                ans = get(f"{self.url}{w}",verify=False)
                self.requestsMade+=1

                if ans.status_code in self.validStatusCodes:
                    self.addFoundDir(w,ans)

                for ext in self.extensions:
                    ans = get(f"{self.url}{w}.{ext}")
                    self.requestsMade+=1
                    if ans.status_code in self.validStatusCodes:
                        self.addFoundDir(f"{w}.{ext}",ans)
                continue
        elif not self.extensions and self.rules:
            for w in arr:
                if stop_threads_event.is_set(): return
                ans = get(f"{self.url}{w}",verify=False)
                if ans.status_code in self.validStatusCodes:
                    self.extractData(w,ans)
                self.requestsMade+=1
                continue
        elif not self.extensions and not self.rules:
            for w in arr:
                if stop_threads_event.is_set(): return
                ans = get(f"{self.url}{w}",verify=False)
                self.requestsMade+=1
                if ans.status_code in self.validStatusCodes:
                    self.addFoundDir(w,ans)
                continue
        # Thread ended
        self.finishedThreads+=1

    def addFoundDir(self,path,ans):
        self.currentTarget['found routes'].append({'name':path,'status':ans.status_code,'Content type':ans.headers['Content-type'],'Length':ans.headers['Content-Length']})
    
    def extractData(self,path,ans):
        data = []
        for rule in open(self.rules):
            print(f"Rule => {rule}")
            data.append(findall(compile(rule),BeautifulSoup(ans.content,'html.parser').text))    
        if data:
            self.currentTarget['found routes'].append({'name':path,'status':ans.status_code,'Content type':ans.headers['Content-type'],'Length':ans.headers['Content-Length']})
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
                mythreads.append(Thread(target=self.pathBuster,args=(wlArray[begL:begL+wpt],)))
                begL+=wpt
            mythreads.append(Thread(target=self.pathBuster,args=(wlArray[begL:],)))

            for th in mythreads:
                th.start()

            # Keep main thread sleeping until others end or ctrl+c
            # is pressed, in that case the stop_threads_event will
            # be set and threads will terminate their execution(line 91)
            while not stop_threads_event.is_set() and self.finishedThreads != self.threadC:
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
