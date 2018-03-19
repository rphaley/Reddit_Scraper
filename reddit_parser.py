#TODO

import requests, json, time, random, threading, re, datetime
from sendEmail import sendEmail




def check(site):
    #Phrases to Exclude from Titles
    blstFlair =[]
    blstTitle =[]
    winVer = ['5.2','6.0','6.1','6.2','6.3','10.0']
    timeLow = 300
    timeHigh = 600
    OLDResponse = ''
    CN = re.findall('r\/\w{2}',site)
    CN = CN[0][2:]
    while True:
        try:
            response = requests.get(site, verify=True, timeout=5,headers = {'User-agent': 'Mozilla/5.0 (Windows NT {}; Win64; x64;)'.format(random.choice(winVer))})
        except Exception as e:
            print("Client Error retrieving web data from {} Reason:{}".format(CN,e))
        #Check for Errors
        if response.content == b'{"message": "Too Many Requests", "error": 429}':
            print("Reddit error requests from {}".format(CN))
        elif response.status_code != 200:
            print("Server Error retrieving web data from {}".format(CN))
            time.sleep(random.randint(timeLow,timeHigh))
            continue
        #Parse output
        parsed_json = json.loads(response.content)

        #Check if data changed since last visit
        h = 0
        while True:
            bad = 0
            #Get timestamp
            tStamp = datetime.datetime.now()
            #Check is thread is stickied, ignore
            if parsed_json['data']['children'][h]['data']['stickied'] == True:
                print('Stickied Thread in {}, ignoring'.format(CN))
                h += 1
                continue
            #Ignore thread change
            elif parsed_json['data']['children'][h]['data']['title'] == OLDResponse:
                print('[{:%H:%M %m/%d/%y}]Thread {} has not changed, ignore'.format(tStamp,CN))
                bad = 1
                h += 1
                break
            #Thread has changed, update
            else:
                print('[{:%H:%M %m/%d/%y}]Thread {} has changed, updating'.format(tStamp,CN))
                i = h
                OLDResponse = parsed_json['data']['children'][h]['data']['title']
                break
        if bad == 1:
            time.sleep(random.randint(timeLow,timeHigh))
            continue

        #Parse specific output
        flair = parsed_json['data']['children'][i]['data']['link_flair_text']
        title = parsed_json['data']['children'][i]['data']['title']
        url = parsed_json['data']['children'][i]['data']['url']
        title = title.upper()

        #Check in title (if no flair found)
        if not flair:
            for j in blstTitle:
                if j in title:
                    bad = 1
                    break
            if bad == 0:
                sendEmail('{}\n'.format(title),url,CN)
                try:
                    print('[REDDIT]{}\n{}\n'.format(title,url))
                except:
                    print('[REDDIT]{}\n'.format(url))
            continue
        #Check in flair
        flair = flair.upper()
        for k in blstFlair:
            if k in flair:
                bad = 1
                break
        if bad == 0 and flair[0]!='M':
            sendEmail('[{}] {}'.format(flair,title),url,CN)
            try:
                print('[REDDIT][{}] {}\n{}\n'.format(flair,title,url))
            except:
                print('[REDDIT]{}\n'.format(url))
            continue
        print("Check Complete on {}".format(CN))
        time.sleep(random.randint(timeLow,timeHigh))


def Hosts(sites):
    threads = []
    for uri in sites:
        print("Trying {}...".format(uri))
        t = threading.Thread(target=check, args=(uri,)) #Create thread for each host
        t.daemon = True             #kill process if main thread ends
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

if __name__ == "__main__":
    sites = []
    Hosts(sites)
