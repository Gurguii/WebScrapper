# NOTE  
At first I thought I wouldn't spend much more time reviewing the code and doing some changes but I've been last 2 days completly obsessed with performance improvement. But I haven't gotten much better results :(. I'll try to improve data manipulation using numpy/pandas this weekend(while also trying to keep pathbuster functions as clear as possible) and leave a basic but useful tool(hopefully)
# WebScrapper
Basic Python web scrapper which allows enumerating routes on a website and extract data using regex. Outputs found data (routes and regex matches) on a json format.  
I'm willing to add stuff such as being able to receive a bunch of targets, maybe colored output?.  
#### Note: I made this using classes because I'm thinking about making a small lib with this and some other features or idk and so I wanted to practise classes and some of it features such as overloading (which I ended up removing).  

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
#### -target / --target <string,file,csv> - Target/s 
#### -h / --help - Prints help message(not properly made yet) and exits.  
#### -p / --port <int> - Sets target port, default 80  
#### -t / --threads <int> - Sets amount of threads, default 10  
#### -ext / --extensions <comma,separated,extensions> - Do an additional /<word>.<extension> request for each extension  
#### -r / --rules <file> - Whenever a valid status code is gotten from a path, get content matching any of the rules in given file  
#### -sc / --status-codes <comma,separated,ints> - Sets valid status codes, default 200 and 301
#### -ssl / --ssl - Do https requests (This does not change port to 443)
