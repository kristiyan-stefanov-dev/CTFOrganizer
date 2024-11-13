import json
import requests
import shutil
import os
from datetime import datetime
from termcolor import colored
import string
import wexpect
import time

os.system('color')

with open("config.txt", "r") as file:
    config = file.read().splitlines()

archiveFilesList = []
handledTypes = [
    "application/zip",
    'application/x-tar',
    'application/gzip',
    'application/x-bzip2'
]

def extractArchive(contentType, filePath):
    filename = os.path.basename(filePath)
    extractPath = os.path.dirname(filePath)
    print(colored(f"Extracting {filename} archive...", "blue"), end=" ")

    shutil.unpack_archive(filePath, extractPath)
    print(colored(f"done.", "green"))

def downloadFile(url, outputPath, contentType):
    filename = url.split('/')[-1].split("?")[0]
    print(f"    - {filename}", end=" ")
    outputPath = os.path.join(outputPath, filename)

    if os.path.exists(outputPath):
        print(colored(f"    already exists.", "grey"))
        return
    
    with requests.get(url, stream=True) as r:
        with open(outputPath, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
            print(colored(f"    done.", "green"))

        if filename.endswith(".sol"):
            currDir = os.path.dirname(outputPath)
            copyPath = os.path.join(currDir, f"../Solution/hardhat/contracts/{filename}")

            shutil.copy(outputPath, copyPath)

    if contentType in handledTypes:
        archiveFilesList.append({
            "contentType": contentType,
            "file": outputPath
        })

def createFolder(outputPath):
    if not os.path.exists(outputPath):
        os.makedirs(outputPath)
        print(f"Folder '{outputPath}' created.")
        return True
    
    print(colored(f"Folder '{outputPath}' already exists.", "grey"))
    return False

outputPath = config[0].split(" = ")[1]
ctfName = config[1].split(" = ")[1]
url = config[2].split(" = ")[1].replace("\"", "")
cookies = json.loads(config[3].split(" = ")[1])
headers = json.loads(config[4].split(" = ")[1])

baseChallengesPath = os.path.join(outputPath, str(datetime.now().month))
createFolder(baseChallengesPath)

baseChallengesPath = os.path.join(baseChallengesPath, ctfName)
createFolder(baseChallengesPath)

session = requests.session()

challengesRes = session.get(url, headers=headers, cookies=cookies)
challenges = json.loads(challengesRes.text)["data"]

challengeIDs = [challenge["id"] for challenge in challenges]
print(colored(f"Total challenges: {len(challengeIDs)}", "yellow"))

files = {}

for challengeID in challengeIDs:
    challengeRes = session.get(f"{url}/{challengeID}", headers=headers, cookies=cookies).json()
    challengeData = challengeRes["data"]

    originalChallengeName = challengeData["name"]
    originalCategory = challengeData["category"]
    challengeName = challengeData["name"].translate(str.maketrans('', '', string.punctuation)).strip().replace(" ", "_")
    category = challengeData["category"].translate(str.maketrans('', '', string.punctuation)).strip().replace(" ", "_").capitalize()
    description = challengeData["description"]

    challengePath = os.path.join(baseChallengesPath, category)
    createFolder(challengePath)

    challengePath = os.path.join(challengePath, challengeName)
    challengeFilesPath = os.path.join(challengePath, "Files")
    challengeSolutionPath = os.path.join(challengePath, "Solution")
            
    createFolder(challengePath)

    if challengeData["files"]:
        createFolder(challengeFilesPath)
    
    createFolder(challengeSolutionPath)

    with open(os.path.join(challengeSolutionPath, "Challenge.md"), "w", encoding="utf-8") as file:
        file.write(f"# {originalChallengeName} - {originalCategory}\n")
        file.write(f"{description}")

    with open(os.path.join(challengeSolutionPath, "Notes.md"), "w", encoding="utf-8") as file:
        file.write("Notes:\n")

    if "blockchain" in category.lower():
        print(colored(f"Blockchain challenge '{originalChallengeName}' detected.", "red"))
        print(colored(f"Initializing hardhat setup", "blue"), end=" ")
        
        hardhatPath = os.path.join(challengeSolutionPath, "hardhat")
        if createFolder(hardhatPath):
            try:
                
                child = wexpect.spawn(f'npx hardhat init', cwd=hardhatPath)
                child.expect('What do you want to do?')
                child.sendline("0")
                child.expect('Hardhat project root:')
                child.sendline("")
                child.expect('a .gitignore?')
                child.sendline("y")
                child.expect('\\?')
                child.sendline("y")
                child.expect("dependencies with npm")
                child.sendline("n")

                print(colored(f"done.", "green"))
            except Exception as e:
                print(colored(f"Error initializing hardhat setup: {e}", "red"))

    print(colored(f"Challenge '{originalChallengeName}' created.", "green"))

    if challengeData["files"]:
        filesSize = 0
        downloadUrls = []


        for file in challengeData["files"]:
            parts = url.split('/')
            base_url = '/'.join(parts[:3])
            res = session.get(f"{base_url}/{file}")
            filesSize += int(res.headers.get('content-length', 0))
            contentType = res.headers.get('content-type', "unknown")
            
            downloadUrls.append(f"{base_url}/{file}")

        files[str(challengeID)] = {
            "totalSize": filesSize,
            "files": downloadUrls,
            "outputPath": challengeFilesPath,
            "challengeName": originalChallengeName,
            "contentType": contentType,
        }

totalDownloadSize = sum(files[str(challengeID)]["totalSize"] for challengeID in files)

print(colored(f"Total download size: {(totalDownloadSize / 1024 / 1024):.2f} MB", "yellow"))

files = sorted(files.items(), key=lambda x: x[1]["totalSize"])

for challenge in files:
    print(colored(f"Downloading files for '{challenge[1]['challengeName']}'", "yellow"))
    for file in challenge[1]["files"]:
        downloadFile(file, challenge[1]["outputPath"], challenge[1]["contentType"])

if archiveFilesList:
    for file in archiveFilesList:
        extractArchive(file["contentType"], file["file"])