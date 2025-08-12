from PIL import Image
from io import BytesIO
import time
import requests as req
import re
import random
import string
from art import *
import freedns
import sys
import argparse
import pytesseract
import copy
from PIL import ImageFilter
import os
import platform
from importlib.metadata import version
import lolpython
import time

# Hardcoded configuration - no more argument parsing needed
class Config:
    # Fixed settings
    ip = "15.204.209.18"
    use_tor = True  # Automatically use Tor for anonymity
    # Make sure Tor is running on port 9050 for this to work
    auto = True
    webhook = "none"
    proxy = False
    silent = False
    outfile = "domainlist.txt"
    type = "A"
    pages = "1-10"  # Default page range
    subdomains = "random"  # Will be loaded from GitHub
    number = 100  # Number of domains to create

# Create a mock args object to maintain compatibility
class MockArgs:
    def __init__(self, config):
        self.ip = config.ip
        self.use_tor = config.use_tor
        self.auto = config.auto
        self.webhook = config.webhook
        self.proxy = config.proxy
        self.silent = config.silent
        self.outfile = config.outfile
        self.type = config.type
        self.pages = config.pages
        self.subdomains = config.subdomains
        self.number = config.number
        self.single_tld = None

config = Config()
args = MockArgs(config)

ip = args.ip
if not args.silent:
    lolpython.lol_py(text2art("domainmaker"))
    print("made with <3 by Cbass92")
    print("🔒 Tor Mode: ENABLED - All connections will go through Tor for anonymity")
    print("💡 Make sure Tor is running on port 9050 for this to work")
    print("💡 If Tor fails, the script will automatically fall back to direct connection")
    time.sleep(2)

def checkprint(input):
    global args
    if not args.silent:
        print(input)

client = freedns.Client()

checkprint("client initialized")

def get_data_path():
    script_dir = os.path.dirname(__file__)
    checkprint("checking os")
    if platform.system() == "Windows":
        filename = os.path.join(script_dir, "data", "windows", "tesseract")
    elif platform.system() == "Linux":
        filename = os.path.join(script_dir, "data", "tesseract-linux")
    else:
        print(
            "Unsupported OS. This could cause errors with captcha solving. Please install tesseract manually."
        )
        return None
    os.environ["TESSDATA_PREFIX"] = os.path.join(script_dir, "data")
    return filename

path = get_data_path()
if path:
    pytesseract.pytesseract.tesseract_cmd = path
    checkprint(f"Using tesseract executable: {path}")
else:
    checkprint("No valid tesseract file for this OS.")

domainlist = []
domainnames = []
checkprint("getting ip list")
iplist = req.get(
    "https://raw.githubusercontent.com/sebastian-92/byod-ip/refs/heads/master/byod.json"
).text
iplist = eval(iplist)

# Load bean names from GitHub
def load_bean_names():
    try:
        response = req.get("https://raw.githubusercontent.com/MYNAMEINBEAN/all-names/refs/heads/main/for-void.txt")
        if response.status_code == 200:
            bean_names = response.text.strip().split(',')
            checkprint(f"Loaded {len(bean_names)} bean names from GitHub")
            return bean_names
        else:
            checkprint("Failed to load bean names from GitHub, using random subdomains")
            return None
    except Exception as e:
        checkprint(f"Error loading bean names: {e}, using random subdomains")
        return None

# Load bean names at startup
bean_names = load_bean_names()

def test_connection():
    """Test if we can connect to freedns.afraid.org"""
    checkprint("🔍 Testing connection to freedns.afraid.org...")
    try:
        # Use the same session as the client to test with Tor if enabled
        if args.use_tor and client.session.proxies:
            checkprint("🌐 Testing connection through Tor...")
            response = client.session.get("https://freedns.afraid.org", timeout=15)
        else:
            checkprint("🌐 Testing direct connection...")
            response = req.get("https://freedns.afraid.org", timeout=10)
        
        if response.status_code == 200:
            checkprint("✅ Connection test successful!")
            if args.use_tor and client.session.proxies:
                checkprint("🔒 Connection is working through Tor!")
            else:
                checkprint("🌐 Connection is working directly!")
            return True
        else:
            checkprint(f"❌ Connection test failed with status code: {response.status_code}")
            return False
    except Exception as e:
        checkprint(f"❌ Connection test failed: {e}")
        if args.use_tor:
            checkprint("💡 This might be a Tor connection issue")
            checkprint("💡 Make sure Tor is running and accessible on port 9050")
        return False

def getpagelist(arg):
    arg = arg.strip()
    if "," in arg:
        arglist = arg.split(",")
        pagelist = []
        for item in arglist:
            if "-" in item:
                sublist = item.split("-")
                if len(sublist) == 2:
                    sp = int(sublist[0])
                    ep = int(sublist[1])
                    if sp < 1 or sp > ep:
                        checkprint("Invalid page range: " + item)
                        sys.exit()
                    pagelist.extend(range(sp, ep + 1))
                else:
                    checkprint("Invalid page range: " + item)
                    sys.exit()
        return pagelist
    elif "-" in arg:
        pagelist = []
        sublist = arg.split("-")
        if len(sublist) == 2:
            sp = int(sublist[0])
            ep = int(sublist[1])
            if sp < 1 or sp > ep:
                checkprint("Invalid page range: " + arg)
                sys.exit()
            pagelist.extend(range(sp, ep + 1))
        else:
            checkprint("Invalid page range: " + arg)
            sys.exit()
        return pagelist
    else:
        return [int(arg)]

def getdomains(arg):
    global domainlist, domainnames
    for sp in getpagelist(arg):
        checkprint("getting page " + str(sp))
        html = req.get(
            "https://freedns.afraid.org/domain/registry/?page="
            + str(sp)
            + "&sort=2&q=",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "max-age=0",
                "Connection": "keep-alive",
                "DNT": "1",
                "Host": "freedns.afraid.org",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "sec-ch-ua": '"Not;A=Brand";v="24", "Chromium";v="128"',
                "sec-ch-ua-platform": "Linux",
            },
        ).text
        pattern = r"<a href=\/subdomain\/edit\.php\?edit_domain_id=(\d+)>([\w.-]+)<\/a>(.+\..+)<td>public<\/td>"
        matches = re.findall(pattern, html)
        domainnames.extend([match[1] for match in matches])
        domainlist.extend([match[0] for match in matches])

def find_domain_id(domain_name):
    page = 1
    html = req.get(
        "https://freedns.afraid.org/domain/registry/?page="
        + str(page)
        + "&q="
        + domain_name,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "DNT": "1",
            "Host": "freedns.afraid.org",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not;A=Brand";v="24", "Chromium";v="128"',
                "sec-ch-ua-platform": "Linux",
        },
    ).text
    pattern = r"<a href=\/subdomain\/edit\.php\?edit_domain_id=([0-9]+)><font color=red>(?:.+\..+)<\/font><\/a>"
    matches = re.findall(pattern, html)
    if len(matches) > 0:
        checkprint(f"Found domain ID: {matches[0]}")
    else:
        raise Exception("Domain ID not found")
    return matches[0]

hookbool = False
webhook = ""
if args.subdomains != "random":
    checkprint("Subdomains set to:")
    checkprint(args.subdomains.split(","))
checkprint("ready")

def getcaptcha():
    return Image.open(BytesIO(client.get_captcha()))

def denoise(img):
    imgarr = img.load()
    newimg = Image.new("RGB", img.size)
    newimgarr = newimg.load()
    dvs = []
    for y in range(img.height):
        for x in range(img.width):
            r = imgarr[x, y][0]
            g = imgarr[x, y][1]
            b = imgarr[x, y][2]
            if (r, g, b) == (255, 255, 255):
                newimgarr[x, y] = (r, g, b)
            elif ((r + g + b) / 3) == (112):
                newimgarr[x, y] = (255, 255, 255)
                dvs.append((x, y))
            else:
                newimgarr[x, y] = (0, 0, 0)

    backup = copy.deepcopy(newimg)
    backup = backup.load()
    for y in range(img.height):
        for x in range(img.width):
            if newimgarr[x, y] == (255, 255, 255):
                continue
            black_neighbors = 0
            for ny in range(max(0, y - 2), min(img.height, y + 2)):
                for nx in range(max(0, x - 2), min(img.width, x + 2)):
                    if backup[nx, ny] == (0, 0, 0):
                        black_neighbors += 1
            if black_neighbors <= 5:
                newimgarr[x, y] = (255, 255, 255)
    for x, y in dvs:
        black_neighbors = 0
        for ny in range(max(0, y - 2), min(img.height, y + 2)):
            for nx in range(max(0, x - 1), min(img.width, x + 1)):
                if newimgarr[nx, ny] == (0, 0, 0):
                    black_neighbors += 1
            if black_neighbors >= 5:
                newimgarr[x, y] = (0, 0, 0)
            else:
                newimgarr[x, y] = (255, 255, 255)
    width, height = newimg.size
    black_pixels = set()
    for y in range(height):
        for x in range(width):
            if newimgarr[x, y] == (0, 0, 0):
                black_pixels.add((x, y))

    for x, y in list(black_pixels):
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in black_pixels:
                newimgarr[nx, ny] = 0
    backup = copy.deepcopy(newimg)
    backup = backup.load()
    for y in range(img.height):
        for x in range(img.width):
            if newimgarr[x, y] == (255, 255, 255):
                continue
            black_neighbors = 0
            for ny in range(max(0, y - 2), min(img.height, y + 2)):
                for nx in range(max(0, x - 2), min(img.width, x + 2)):
                    if backup[nx, ny] == (0, 0, 0):
                        black_neighbors += 1
            if black_neighbors <= 6:
                newimgarr[x, y] = (255, 255, 255)
    return newimg

def solve(image):
    image = denoise(image)
    text = pytesseract.image_to_string(
        image.filter(ImageFilter.GaussianBlur(1))
        .convert("1")
        .filter(ImageFilter.RankFilter(3, 3)),
        config="-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ --psm 13 -l freednsocr",
    )
    text = text.strip().upper()
    checkprint("captcha solved: " + text)
    if len(text) != 5 and len(text) != 4:
        checkprint("captcha doesn't match correct pattern, trying different captcha")
        text = solve(getcaptcha())
    return text

def generate_random_string(length):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))

def login():
    while True:
        try:
            checkprint("getting captcha")
            image = getcaptcha()
            if args.auto:
                capcha = solve(image)
                checkprint("captcha solved (hopefully)")
            else:
                checkprint("showing captcha")
                image.show()
                capcha = input("Enter the captcha code: ")
            checkprint("generating email")
            stuff = req.get(
                "https://api.guerrillamail.com/ajax.php?f=get_email_address"
            ).json()
            email = stuff["email_addr"]
            checkprint("email address generated email:" + email)
            checkprint(email)
            checkprint("creating account")
            username = generate_random_string(13)
            client.create_account(
                capcha,
                generate_random_string(13),
                generate_random_string(13),
                username,
                "pegleg1234",
                email,
            )
            checkprint("activation email sent")
            checkprint("waiting for email")
            hasnotreceived = True
            while hasnotreceived:
                nerd = req.get(
                    "https://api.guerrillamail.com/ajax.php?f=check_email&seq=0&sid_token="
                    + str(stuff["sid_token"])
                ).json()

                if int(nerd["count"]) > 0:
                    checkprint("email received")
                    mail = req.get(
                        "https://api.guerrillamail.com/ajax.php?f=fetch_email&email_id="
                        + str(nerd["list"][0]["mail_id"])
                        + "&sid_token="
                        + str(stuff["sid_token"])
                    ).json()
                    match = re.search(r'\?([^">]+)"', mail["mail_body"])
                    if match:
                        checkprint("code found")
                        checkprint("verification code: " + match.group(1))
                        checkprint("activating account")
                        client.activate_account(match.group(1))
                        checkprint("accout activated")
                        time.sleep(1)
                        checkprint("attempting login")
                        client.login(email, "pegleg1234")
                        checkprint("login successful")
                        hasnotreceived = False
                    else:
                        checkprint(
                            "no match in email! you should generally never get this."
                        )
                        checkprint("error!")

                else:
                    checkprint("checked email")
                    time.sleep(2)
        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            checkprint("Got error while creating account: " + repr(e))
            if "Connection" in str(e) or "SOCKS" in str(e):
                checkprint("Connection error detected - this might be a proxy/Tor issue")
                if args.use_tor:
                    checkprint("Disabling Tor and trying direct connection")
                    args.use_tor = False
                    client.session.proxies.clear()
                    checkprint("Retrying with direct connection...")
                    continue
                else:
                    checkprint("Already using direct connection, this might be a network issue")
                    checkprint("Waiting 10 seconds before retry...")
                    time.sleep(10)
                    continue
            elif args.use_tor:
                checkprint("attempting to change tor identity")
                try:
                    from stem import Signal
                    from stem.control import Controller

                    with Controller.from_port(port=9051) as controller:
                        controller.authenticate()
                        controller.signal(Signal.NEWNYM)
                        time.sleep(controller.get_newnym_wait())
                        checkprint("tor identity changed")
                except Exception as e:
                    checkprint("Got error while changing tor identity: " + repr(e))
                    continue
            continue
        else:
            break

def createlinks(number):
    for i in range(number):
        if i % 5 == 0:
            if args.use_tor:
                checkprint("attempting to change tor identity")
                try:
                    from stem import Signal
                    from stem.control import Controller

                    with Controller.from_port(port=9051) as controller:
                        controller.authenticate()
                        controller.signal(Signal.NEWNYM)
                        time.sleep(controller.get_newnym_wait())
                        checkprint("tor identity changed")
                except Exception as e:
                    checkprint("Got error while changing tor identity: " + repr(e))
                    checkprint("Disabling Tor and continuing with direct connection")
                    args.use_tor = False
                    client.session.proxies.clear()
            login()
        createdomain()

def createmax():
    login()
    checkprint("logged in")
    checkprint("creating domains")
    createdomain()
    createdomain()
    createdomain()
    createdomain()
    createdomain()

def createdomain():
    while True:
        try:
            image = getcaptcha()
            if args.auto:
                capcha = solve(image)
                checkprint("captcha solved")
            else:
                checkprint("showing captcha")
                image.show()
                capcha = input("Enter the captcha code: ")

            if args.single_tld:
                random_domain_id = non_random_domain_id
            else:
                random_domain_id = random.choice(domainlist)
            
            # Use bean names if available, otherwise random
            if bean_names:
                subdomainy = random.choice(bean_names)
            else:
                if args.subdomains == "random":
                    subdomainy = generate_random_string(10)
                else:
                    subdomainy = random.choice(args.subdomains.split(","))
            
            client.create_subdomain(capcha, args.type, subdomainy, random_domain_id, ip)
            tld = args.single_tld or domainnames[domainlist.index(random_domain_id)]
            checkprint("domain created")
            checkprint("link: http://" + subdomainy + "." + tld)
            domainsdb = open(args.outfile, "a")
            domainsdb.write("\nhttp://" + subdomainy + "." + tld)
            domainsdb.close()
            if hookbool:
                checkprint("notifying webhook")
                req.post(
                    webhook,
                    json={
                        "content": "Domain created:\nhttp://"
                        + subdomainy
                        + "."
                        + tld
                        + "\n ip: "
                        + ip
                    },
                )
                checkprint("webhook notified")
        except KeyboardInterrupt:
            # quit
            sys.exit()
        except Exception as e:
            checkprint("Got error while creating domain: " + repr(e))
            continue
        else:
            break

non_random_domain_id = None

def finddomains(pagearg):
    pages = pagearg.split(",")
    for page in pages:
        getdomains(page)

def init():
    global args, ip, iplist, webhook, hookbool, non_random_domain_id
    
    # Set IP directly
    ip = args.ip
    checkprint(f"Using IP: {ip}")
    
    # Set webhook to none
    hookbool = False
    webhook = "none"
    checkprint("Webhook disabled")
    
    # Set proxy to false (using Tor instead)
    args.proxy = False
    checkprint("Proxy disabled, using Tor")
    
    # Set auto captcha solving
    args.auto = True
    checkprint("Auto captcha solving enabled")
    
    # Set Tor proxy
    if args.use_tor:
        checkprint("🔒 Setting up Tor connection for anonymity...")
        try:
            proxies = {
                "http": "socks5h://127.0.0.1:9050",
                "https": "socks5h://127.0.0.1:9050",
            }
            client.session.proxies.update(proxies)
            checkprint("✅ Tor proxy set successfully!")
            checkprint("🌐 All connections will now go through Tor")
        except Exception as e:
            checkprint(f"❌ Failed to set Tor proxy: {e}")
            checkprint("⚠️  Falling back to direct connection")
            checkprint("💡 To use Tor, make sure it's running on port 9050")
            args.use_tor = False
            client.session.proxies.clear()
    else:
        checkprint("🌐 Using direct connection (no proxy)")
        client.session.proxies.clear()
    
    # Test connection before proceeding
    if not test_connection():
        if args.use_tor:
            checkprint("⚠️  Tor connection test failed!")
            checkprint("💡 This usually means Tor is not running or not accessible")
            checkprint("💡 To fix this:")
            checkprint("   1. Download Tor Browser from https://www.torproject.org/")
            checkprint("   2. Start Tor and make sure it's running on port 9050")
            checkprint("   3. Or run: python enable_tor.py to disable Tor temporarily")
            checkprint("🔄 Retrying with direct connection...")
            args.use_tor = False
            client.session.proxies.clear()
            if test_connection():
                checkprint("✅ Direct connection works! Continuing without Tor...")
            else:
                checkprint("❌ Both Tor and direct connection failed!")
                checkprint("💡 Please check your internet connection")
        else:
            checkprint("❌ Connection test failed. Please check your internet connection.")
        checkprint("Continuing anyway, but this might cause issues...")
    else:
        checkprint("✅ Connection test passed! Ready to proceed...")
    
    # Load domains
    finddomains(args.pages)
    
    # Create the specified number of links
    if args.number:
        createlinks(args.number)

def chooseFrom(dictionary, message):
    checkprint(message)
    for i, key in enumerate(dictionary.keys()):
        checkprint(f"{i+1}. {key}")
    choice = int(input("Choose an option by number: "))
    return list(dictionary.keys())[choice - 1]

if __name__ == "__main__":
    init()
