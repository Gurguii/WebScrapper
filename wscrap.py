import signal
from os import path
from requests import get
from re import compile, findall
from threading import Thread, Event
from bs4 import BeautifulSoup
from sys import argv
from time import sleep
from json import dumps

stop_threads_event = Event()
requests_made = 0

def ctrlC(i,f):
    print("\n\nUser pressed ctrl+c ...")
    ws.printInfo()
    stop_threads_event.set()
    exit(0)

def help():
    print(f"Usage: {argv[0]} <options> <target>")
    exit(0)

class ArgumentParser():
    def __init__(self):
        if len(argv) == 1:help()
        # Set target and default values
        # of options that have'em
        self.target = argv[-1]
        self.threadC = 10
        self.port = 80
        self.validStatusCodes = (200,301)
        self.wordlist = '' # file
        self.rules = '' # file
        self.extensions = '' # tuple
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
            exit(0)

        if not path.exists(self.wordlist):
            print(f"[+] Wordlist {self.wordlist} doesn't exist")
            exit(0)

        try:
            self.port = int(self.port)
            self.threadC = int(self.threadC)
        except ValueError as err:
            print(f"[+] Port and thread amount must be integers => {err}")
            exit(0)
            
        # Set url after parsing/sanitizing arguments in case we have to end the execution or change default port 
        self.url = f"http://{self.target}:{self.port}/"

class WebScrapper(ArgumentParser):
    def __init__(self):
        super().__init__()
        self.dataExtracted = {self.target: {}}
        self.finishedThreads = 0

    def pathBuster(self, begL, Lamount):
        global requests_made
        with open(self.wordlist) as file:

            for i in range(begL):
                next(file)

            for w in [next(file).strip() for i in range (Lamount)]:
                if stop_threads_event.is_set():return

                ans = get(self.url+w)
                sc = ans.status_code
                requests_made+=1

                if sc in self.validStatusCodes: 
                    self.addFoundDir(w,ans)
                    if self.rules:
                        self.extractData(w,BeautifulSoup(ans.content,'html.parser').text)
                
                if self.extensions:
                    for ext in self.extensions:
                        url = f"http://{self.target}:{self.port}/{w}.{ext}"
                        ans = get(url)
                        requests_made+=1
                        if ans.status_code in self.validStatusCodes: 
                            self.addFoundDir(f"{w}.{ext}",ans)
                            if self.rules:
                                self.extractData(f"{w}.{ext}",BeautifulSoup(ans.content,'html.parser').text)
        # Thread ended
        self.finishedThreads+=1

    def addFoundDir(self,word,ans):
        self.dataExtracted[self.target][word] = {"Status code":ans.status_code,"Content type":ans.headers['Content-type'],"Length":ans.headers['Content-Length']}

    def extractData(self,word,content):
        for rule in open(self.rules):
            data = findall(compile(rule),content)
            if data:
                self.dataExtracted[self.target][word]["Data extracted"] = data

    def printInfo(self):
        print("\n"+dumps(self.dataExtracted, sort_keys=True, indent=4))

    def runThreads(self):
        fileLines = 0; begL = 1; mythreads = []; 
        for i in open(self.wordlist):fileLines+=1
        linesPerThread = int(fileLines/self.threadC)

        # Add amount of threads required
        for i in range (self.threadC-1):
            mythreads.append(Thread(target=self.pathBuster,args=(begL,linesPerThread)))
            begL+=linesPerThread
        mythreads.append(Thread(target=self.pathBuster,args=(begL-1,linesPerThread+int(fileLines%ws.threadC))))

        print(f"[!] Starting {self.threadC} threads...")

        # Start threads
        for th in mythreads:
            th.start()

        # Keep main thread sleeping until others end or ctrl+c
        # is pressed, in that case the stop_threads_event will
        # be set and threads will terminate their execution(line 71)
        total_requests = fileLines+(fileLines*len(self.extensions))           
        while not stop_threads_event.is_set() and self.finishedThreads != self.threadC:
            print(f"Requests: {requests_made}/{total_requests}",end='\r')
            sleep(0.5)
        print(f"Requests: {requests_made}/{total_requests}")

# ctrl+c signal handler
signal.signal(signal.SIGINT,ctrlC)

# Create an WebScrapper instance that will call
# ArgumentParser constructor to parse user
# arguments and start threads. 
ws = WebScrapper()
ws.runThreads()
ws.printInfo()
