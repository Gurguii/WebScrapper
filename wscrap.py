import signal
import numpy as np
import sys
from os import path
from requests import get
from re import compile, findall
from threading import Thread, Event
from bs4 import BeautifulSoup
from sys import argv
from time import sleep
from json import dumps
from functools import reduce

stop_threads_event = Event()
requests_made = 0
ISFILE = lambda file : path.exists(file)

def ctrlC(i,f):
    print("\n\nUser pressed ctrl+c ...")
    ws.printInfo()
    stop_threads_event.set()
    sys.exit()

def help():
    print(f"Usage: {argv[0]} <options> <target>")
    sys.exit()

class ArgumentParser():
    def __init__(self):
        if len(argv) == 1:help()
        # Set target and default values
        # of options that have'em
        self.targets = argv[-1]
        self.threadC = 10
        self.port = 80
        self.validStatusCodes = (200,301)
        self.wordlist = '' # file
        self.rules = '' # file
        self.extensions = '' # tuple
        self.url = ''
        for n in range(1,len(argv)):
            match argv[n]:
                case "-h" | "--help":
                    help()
                case "-p" | "--port":
                    self.port= argv[n+1]
                case "-wl" | "--wordlist":
                    self.wordlist = argv[n+1]
                case "-t" | "--threads":
                    self.threadC = argv[n+1]
                case "-ext" | "--extensions":
                    self.extensions = tuple(argv[n+1].split(','))
                case "-r" | "--rules":
                    self.rules = argv[n+1]
                case "-sc" | "--status-codes":
                    self.validStatusCodes = tuple(argv[n+1].split(','))
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

        try:
            self.port = int(self.port)
            self.threadC = int(self.threadC)
        except ValueError as err:
            print(f"[+] Port and thread amount must be integers => {err}")
            sys.exit()

        if ISFILE(self.targets):
            self.targets = reduce(lambda x,y : x+y, (bytes.decode(x) for x in np.memmap(self.targets,dtype='c'))).split()            

class WebScrapper(ArgumentParser):
    def __init__(self):
        super().__init__()
        self.currentTarget = self.targets[0]
        self.dataExtracted = {}
        self.finishedThreads = 0
    def pathBuster(self, arr):
        global requests_made
        for w in arr:
            # Stop thread execution if user presses ctrl+c
            if stop_threads_event.is_set():return

            ans = get(self.url+w);
            sc = ans.status_code;
            requests_made+=1

            if sc in self.validStatusCodes: 
                self.addFoundDir(w,ans)
                if self.rules:
                    self.extractData(w,BeautifulSoup(ans.content,'html.parser').text)
            
            if self.extensions:
                for ext in self.extensions:
                    url = f"{self.url}/{w}.{ext}"
                    ans = get(url)
                    requests_made+=1
                    if ans.status_code in self.validStatusCodes: 
                        self.addFoundDir(f"{w}.{ext}",ans)
                        if self.rules:
                            self.extractData(f"{w}.{ext}",BeautifulSoup(ans.content,'html.parser').text)
        # Thread ended
        self.finishedThreads+=1

    def addFoundDir(self,word,ans):
        self.dataExtracted[self.currentTarget][word] = {"Status code":ans.status_code,"Content type":ans.headers['Content-type'],"Length":ans.headers['Content-Length']}

    def extractData(self,word,content):
        for rule in open(self.rules):
            data = findall(compile(rule),content)
            if data:
                self.dataExtracted[self.currentTarget][word]["Data extracted"] = data

    def printInfo(self):
        print("\n"+dumps(self.dataExtracted, sort_keys=True, indent=4))

    def runThreads(self):
        # Numpy implementation
        wlArray = reduce(lambda x,y : x+y, (bytes.decode(x) for x in np.memmap(self.wordlist,dtype='c'))).split()
        fileLines = len(wlArray)
        total_requests = len(self.targets)*(fileLines+(fileLines*len(self.extensions))) 

        for t in self.targets:
            print(f"[+] - Starting {self.threadC} threads on target {t}")

            self.url = f"http://{t}:{self.port}/"; self.finishedThreads = 0; self.currentTarget = t; self.dataExtracted[self.currentTarget] = {}
            wpt = int(fileLines/self.threadC); begL = 0; mythreads = []

            for i in range(self.threadC-1):
                mythreads.append(Thread(target=self.pathBuster,args=(np.array(wlArray[begL:begL+wpt]),)))
                begL+=wpt
            mythreads.append(Thread(target=self.pathBuster,args=(np.array(wlArray[begL:]),)))

            for th in mythreads:
                th.start()

            # Keep main thread sleeping until others end or ctrl+c
            # is pressed, in that case the stop_threads_event will
            # be set and threads will terminate their execution(line 88)
                      
            while not stop_threads_event.is_set() and self.finishedThreads != self.threadC:
                print(f"Requests: {requests_made}/{total_requests}",end='\r')
                sleep(1)
            continue
        print(f"Requests: {requests_made}/{total_requests}")

# ctrl+c signal handler
signal.signal(signal.SIGINT,ctrlC)

# Create an WebScrapper instance that will call
# ArgumentParser constructor to parse user
# arguments and start threads. 
ws = WebScrapper()
ws.runThreads()
ws.printInfo()
