# PLEASE READ :)
With the last commit I changed the code structure and added multiprocessing. Pros are now I got rid of the GLI and code is (I think) better structured and faster. Cons are It gave me a headache trying to change the old code(Threads => Processes) so I ended up starting from scratch(recycling some stuff such as ArgumentParser class) and I haven't made a Data Parser as good as I'd like to, but felt like this was a good enough change to commit it :)  
# WebScrapper
Basic Python web scrapper which allows enumerating routes on a website and extract data using regex. Outputs found data (routes and regex matches) on a json format.  
## Setup  
#### Clone the repository
```bash
    sudo git clone https://github.com/Gurguii/WebScrapper
```  
#### Get into the project's directory
```bash
    cd WebScrapper
```  
#### Install requirements (bs4 and requests libraries)  
```bash
    pip3 install -r requirements.txt
```  

## Usage    
```bash
    python3 wscrap.py <options> <target>
```  
#### Note: the -wl/--wordlist <file> option is mandatory
## Options  
#### -t / --target <string,file,csv> - Target/s  
#### -wl / --wordlist <file> - Wordlist to use
#### -h / --help - Prints help message(not properly made yet) and exits.  
#### -p / --port <int> - Sets target port, default 80  
#### -ps / --processes <int> - Sets amount of processes, default 2  
#### -ext / --extensions <comma,separated,extensions> - Do an additional /<word>.<extension> request for each extension  
#### -r / --rules <string,file,csv> - Whenever a valid status code is gotten from a path, get content matching any of the rules in given file  
#### -sc / --status-codes <comma,separated,ints> - Sets valid status codes, default 200 and 301
#### -ssl / --ssl - Do https requests (This does not change port to 443)
