# import time, json, os, yaml, statistics, math, subprocess, threading, shutil
# import sys, platform, requests, time, argparse, platform, utils, tarfile
# from datetime import datetime
# from PIL import Image, ImageDraw

import os, shutil, yaml, datetime, time, subprocess
import tempfile, hashlib, json, requests, tarfile
from PIL import Image, ImageDraw

# ==============================================================================
# Utilities
# ==============================================================================
def match(entity, colorCode):
	try:
		name = entity["name"]
		func = "EXACT"
		if "func" in colorCode:
			func = colorCode["func"]
		
		# Check all names
		for ccName in colorCode["names"]:
			# Handle functions
			match func:
				case "EXACT": 
					if name == ccName: return True
				case "IN": 
					if ccName in name: return True
		return False
	except Exception as e:
		print("ENTITY:", entity)
		print("COLOR CODE:", colorCode)
		exit()



def getFileHash(filePath):
	algorithm = 'sha256'
	func = hashlib.new(algorithm)
	
	with open(filePath, 'rb') as f:
		while chunk := f.read(8192):
			func.update(chunk)
					
	return func.hexdigest()


def ls(folderPath):

	pass


def mkdirs(directory_path):
	try:
		os.makedirs(directory_path)
	except FileExistsError:
		pass


def drawCenterRect(draw, x, y, width=20, height=20, color="red", isSolid = True):
	x1, x2 = x-width /2, x+width /2
	y1, y2 = y-height/2, y+height/2

	if isSolid:
		draw.rectangle(
			[x1, y1, x2, y2], 
			fill = color
		)
	else:
		draw.rectangle(
			[x1, y1, x2, y2], 
			outline = color,
			width = 10
		)


# ==============================================================================
# Main function files
# ==============================================================================
def loadConfig(configPath = "config.yaml"):

	"""
	Loads the config file for the resolution, scale, naming, save file and chunk
	size of the output image
	"""
	# If the config path does not exist, replace it with the default config file
	if os.path.exists(configPath) == False:
		shutil.copy('config-example.yaml', configPath)

	# Load our config file
	with open(configPath, 'r') as f:
		config = yaml.safe_load(f)

	# Add a warning for the config if it is auto generated (default config file)
	if "auto-generated" in config and config["auto-generated"] == True:
		print("Please verify in config.yaml that the settings are correct. Then change auto-generated to False and run again.")
		exit()

	# Add defaults if the keys are not found
	defaults = {
		"factorio-save-path": "/factorio-saves"
	}

	for key in defaults:
		if key not in config:
			config[key] = defaults[key]
	return config


def loadShaderV1(shaderFile = None):
	"""
	Loads a shader file
	"""
	def groupToSelector(groupName):
		if groupName not in config["group"]:
			print(f"ERROR: Group '{groupName}' was not found in '{shaderFile}'")
			exit()
		group = config["group"][groupName]
		names = group["names"]
		func = "EXACT"
		if "func" in group:
			func = group["func"]
		return names, func

	def createConfigEntry(entry, planet=None):
		nonlocal newConfig
		
		# Create defaults
		configEntry = {
			"names": [],
			"func": "EXACT",
			"flags": [],
			"planets": []
		}

		# Figure out the selector
		if "group" in entry: configEntry["names"], configEntry["func"] = groupToSelector(entry["group"])
		if "names" in entry: configEntry["names"] += entry["names"]
		if "name"  in entry: configEntry["names"] += [entry["name"]]
		if planet != None: configEntry["planets"] += [planet]

		# Add the config for this selector
		if "func"  in entry: configEntry["func" ] = entry["func" ]
		if "style" in entry: configEntry["style"] = entry["style"]
		if "size"  in entry: configEntry["size" ] = entry["size" ]
		if "color" in entry: configEntry["color"] = entry["color"]
		if "flags" in entry: configEntry["flags"] = entry["flags"]

		newConfig["entries"].append(configEntry)

	# Load our presets
	with open('presets.yaml', 'r') as f:
		presets = yaml.safe_load(f)

	# Load our shader file
	with open(f'shaders/{shaderFile}', 'r') as f:
		config = yaml.safe_load(f)
		shaderConfig = config

	# Create a config file that the program can better use & work with
	newConfig = {
		"entries": []
	}

	key = "background-color"
	if key in shaderConfig: newConfig[key] = shaderConfig[key]

	# Add the presets first so that they will be replaced
	for entry in presets:
		createConfigEntry(entry)

	# Add the shaders info - Defaults
	if "defaults" in config:
		for entry in config["defaults"]:
			createConfigEntry(entry)

	# Add shader info
	if "planets" in config:
		for planet in config["planets"]:
			for entry in config["planets"][planet]:
				createConfigEntry(entry, planet=planet)

	# Add general entries
	if "general" in config:
		for entry in config["general"]:
			createConfigEntry(entry)
	return newConfig


def useServer():
	"""
	Checks if the server is required to run, if the files have already been
	generated then the pervious files generated from the server are used
	"""
	global currentData
	# Read the last run file
	if os.path.exists(lastRunFilePath) == False:
		return True
	with open(lastRunFilePath, 'r') as file:
		lastRunData = yaml.safe_load(file)

	# Check if the exported files exist
	if os.path.exists("factorio/script-output") == False: return True

	# Check the hash of the save with the last fully ran save
	# Grab the hash of our save file
	currentData = {
		"save-hash": getFileHash(factorioSavePath),
		"chunk-size": config["chunk-size"],
		"scan-range": config["scan-range"]
	}

	if lastRunData != currentData: return True
	
	# Nothing looks amiss, lets use the pervious server files
	return False


def collectServerData():
	"""
	Loads up the Factorio server with the data collection mod to collect the
	required data from the server

	Process
	 - Download and unpack the latest version of the Factorio server
	 - Compile the our data collection mod together with info from our config.yaml
	 - Run the server and wait for the mod indicator flag
	 - Crash the server with the mod when data collection is done
	 - Profit?
	"""
	global currentData
	def updateMod():
		"""
		"Compiles" the mod together with changes from our config
		"""
		print("  Compiling mod...", end="", flush=True)
		if os.path.exists("factorio/mods") == False:
			os.mkdir("factorio/mods")

			# Delete old mod
		modPath = "factorio/mods/CustomMod_0.0.1"
		if os.path.exists(modPath) and os.path.isdir(modPath):
			shutil.rmtree(modPath)

		# Copy new mod
		shutil.copytree("custom-mod", modPath)

		# Add variables in to mod
		with open(f"{modPath}/control.lua", 'r') as file:
			contents = file.read()
		
		contents = contents.replace('$$CHUNK_SIZE$$', str(config["chunk-size"]) if "chunk-size" in config else '512')
		contents = contents.replace('$$SCAN_RANGE$$', str(config["scan-range"]) if "scan-range" in config else '2')

		with open(f"{modPath}/control.lua", 'w') as file:
			# Write the modified contents back to the file
			file.write(contents)

	def updateServer():
		"""
		Pulls the latest version of the Factorio server and extracts it
		"""
		output_path = "factorio.tar.xz"  # Server download path
		if os.path.exists(output_path) == False:
			print("Downloading server...")
			url = "https://factorio.com/get-download/stable/headless/linux64"  # Server download URL
			response = requests.get(url) # Send a GET request to the URL
			if response.status_code != 200: # Check if the request was successful
				print("Response from server {url} was unsuccessfull, the server maybe old")
				return
			
			# Open the output file and write the content of the response to it
			with open(output_path, 'wb') as f:
				f.write(response.content)

		# Delete the old server 
		factorioServerPath = "factorio"
		if os.path.exists(factorioServerPath) and os.path.isdir(factorioServerPath):
			print("  Removing old server path...", end="", flush=True)
			shutil.rmtree(factorioServerPath)
			print(" done.")

		# Extract the new server
		print("  Extracting server file...")
		with tarfile.open("factorio.tar.xz", "r") as tar:
			tar.extractall(path=".", filter='fully_trusted')

	updateServer()
	updateMod()

	# Empty our server output
	scriptOutputPath = "factorio/script-output"
	if os.path.exists(scriptOutputPath):
		shutil.rmtree(scriptOutputPath)
	del scriptOutputPath

	# Remove lock file
	lockFilePath = "factorio/.lock"
	if os.path.exists(lockFilePath):
		print("Removing server lockfile")
		os.remove(lockFilePath)
	del lockFilePath

	# Remove our server log file
	serverLogFile = "logs/factorio.txt"
	if os.path.exists(serverLogFile):
		print("Removing server log file")
		os.remove(serverLogFile)
	del serverLogFile

	# Start up server
	print("Starting Factorio server")
	command = ["factorio/bin/x64/factorio", "--start-server", "/factorio-saves/"+config["factorio-save-name"]+".zip", "--server-settings", "server-settings.json"]
	serverProcess = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	# Calculate the expected number of files
	expectedFiles =  config["scan-range"]*2 + 1
	finishedList = []

	# The line the indicate that the mod is in control of the console output,
	# further lines will be output from the mod
	modIndicator = "b8VmXhHtuENCBh6q"
	flagModLines = False
	surfaceFiles = []
	totalOutput = ""

	while True:
		# ================ Console Display Section ================
		# Check how many files are in each category
		if os.path.exists("factorio/script-output"):
			entries = os.listdir("factorio/script-output")
			print("Folders:")
			for entry in entries:
				full_path = os.path.join("factorio/script-output", entry)
				if os.path.isdir(full_path):
					numOfItems = len(os.listdir(f"factorio/script-output/{entry}"))
					print(entry, numOfItems)
			print()

		# =============== Server Management Section ===============
		# Receive 1024 bytes of data from the pipe at a time
		output_data = serverProcess.stdout.read(1)
		
		if not output_data: break
		
		# Decode the output from bytes to string
		output_str = output_data.decode('utf-8')
		# with open('log-factorio.txt', 'a') as file:
		# 	file.write(output_str)

		totalOutput += output_str

		# Mod indicator reached, start data collection
		if modIndicator in totalOutput:
			totalOutput = totalOutput[totalOutput.index(modIndicator)+len(modIndicator)+2:]
			flagModLines = True
			print("Waiting for server to finish collecting data...\n")
		if flagModLines == False: continue

		# Collect data when new line is reached
		if "\n" in totalOutput:
			line = totalOutput[0:totalOutput.index("\n")]
			totalOutput = totalOutput[totalOutput.index("\n")+2:]

			# Mod intentionally crashed the game
			if "Error ServerMultiplayerManager.cpp" in line: break
			
			if modIndicator not in line and len(line.strip()) > 0:
				surfaceFiles.append(line)

	# Wait for the command to finish and get its final standard error
	final_output, final_error = serverProcess.communicate()
	if final_error: print(f"Error: {final_error.decode('utf-8')}")

	# Write info about this run to the last run file
	with open(lastRunFilePath, 'w') as file:
		yaml.dump(currentData, file, default_flow_style=False)

	return surfaceFiles


def drawImage(surfaceName):
	"""
	Draws an image of a surface with the argument being the data included in the
	drawing
	"""
	def loadSurfaceData():
		# TODO: Fix the file reading, the name of the files changed and this needs to change too 
		# Load our surface data & combine
		bigData = {
			"entities": [],
			"tiles": []
		}
		print(f"  Loading script export files...", end="", flush=True)
		scriptOutputPath = f"factorio/script-output/{surfaceName}"
		if os.path.exists(scriptOutputPath) == False: return None

		# Load all data files, files are broken up in to chunks
		for file in os.listdir(scriptOutputPath):
			# Process matching
			filePath = f"{scriptOutputPath}/{file}"
			print(f"Processing {filePath}")
			with open(filePath, 'r') as file:
				data = json.load(file)

				if "entities" in data:
					bigData["entities"] += data["entities"]
					print(f"  Loaded {len(data['entities'])} entities")
				
				if "tiles" in data:
					bigData["tiles"] += data["tiles"]
					print(f"  Loaded {len(data['tiles'])} entities")
		print(f"Done loaded {len(bigData['entities'])} entities and {len(bigData['tiles'])} tiles")
		print("  done.")
		return bigData

	def getImageInfo(surfaceData):
		"""
		Find info about the entities/tiles that are required to be in the image
		&& 
		Gets all the info for how the image should be drawn, ie finding the correct 
		resolution, scale, rotation, and tile size
		"""
		# Grab all of the cords for use in image center, scale and scope
		print("  Finding scope of surface...", end="", flush=True)
		xCords, yCords = [], []
		for entry in surfaceData["entities"]:
			for shaderConfigEntry in shaderConfig["entries"]:
				if match(entry, shaderConfigEntry) == False: continue
				# print(shaderConfigEntry)
				if "flags" not in shaderConfigEntry: continue
				if "center" not in shaderConfigEntry["flags"]: continue # Make sure that this preset has the center flag
				xCords.append(entry["x"])
				yCords.append(entry["y"])
		print(" done.")

		# Check if there is things to put on the image
		if xCords == [] or yCords == []:
			print("Surface has nothing on it")
			return

		# Move the image center, scale and scope
		# Get the image center
		minx, maxx = min(xCords), max(xCords)
		miny, maxy = min(yCords), max(yCords)
		# imageCenterX = (maxx+minx) / 2
		# imageCenterY = (maxy+miny) / 2
		imageCenterX = (maxx - minx)/2 + minx
		imageCenterY = (maxy - miny)/2 + miny

		# Find the min and max of our image
		tileWidth  = abs(minx) + abs(maxx)
		tileHeight = abs(miny) + abs(maxy)

		return {
			"center": {"x": imageCenterX, "y": imageCenterY},
			# "edge": {
			# 	"top": miny,
			# 	"bottom": maxy,
			# 	"left": minx,
			# 	"right": maxx
			# },
			"size": {
				"width": tileWidth,
				"height": tileHeight
			}
		}

	def drawRect(x, y, width=1, height=1, color = 'red', style = "solid"):
		nonlocal tileSize, draw, imageWidth, imageHeight
		
		drawX = (x*tileSize) + drawCenterX
		drawY = (y*tileSize) + drawCenterY

		drawCenterRect(
			draw = draw,
			x = drawX,
			y = drawY,
			width  = width  * tileSize,
			height = height * tileSize,
			color = color
		)

	# Store unhandled names and tiles to make it easier for shader makers
	unhandledNames = {}

	# Set image resolution info
	tileSize = 1
	imageWidth  = tileSize * int(3500/2) # Default size
	imageHeight = tileSize * int(3500/2) # Default size

	print(f"Drawing surface {surfaceName}...")

	surfaceData = loadSurfaceData()
	if surfaceData == None:
		print("  No data found on surface.")
		return
	imageInfo = getImageInfo(surfaceData)

	# Update the image to match the output
	if "displayZoom" not in debugFlags:
		imageWidth = imageInfo["size"]["width"] * tileSize
		imageHeight = imageInfo["size"]["height"] * tileSize

	# Create our image
	backgroundColor = (0, 0, 0, 0) # Default to black
	imageWidth, imageHeight = int(imageWidth), int(imageHeight)
	image = Image.new('RGBA', (imageWidth, imageHeight), backgroundColor) # Create a new image with a white background
	draw = ImageDraw.Draw(image) # Create a drawing context

	# Get the true draw center
	drawCenterX = int(imageWidth / 2)
	drawCenterY = int(imageHeight/ 2)

	# Draw entities

	# for configEntry in shaderConfig["entries"]:
	# 	print(configEntry)

	renderData = []
	renderData += surfaceData["tiles"]
	renderData += surfaceData["entities"]

	# Sort rendered data so that the tiles are rendered first
	renderData = sorted(renderData, key=lambda x: x['type'], reverse = True)

	for entry in renderData:
		# Set/load default values
		color = None
		style = "solid"
		size = (1, 1)
		x, y = entry["x"], entry["y"]

		if "displayCenter" not in debugFlags:
			x = entry["x"] - (imageInfo["center"]["x"])
			y = entry["y"] - (imageInfo["center"]["y"])

		# Skip this entry if its not in range of the drawn image
		# TODO var/2 is not correct and is over reaching, find the correct formula
		# if x/2 < imageInfo["edge"]["left"  ]: continue
		# if x/2 > imageInfo["edge"]["right" ]: continue
		# if y/2 < imageInfo["edge"]["top"   ]: continue
		# if y/2 > imageInfo["edge"]["bottom"]: continue

		# Check if this entity should be drawn
		for configEntry in shaderConfig["entries"]:
			if len(configEntry["planets"]) > 0 and surfaceName not in configEntry["planets"]: continue

			if match(entry, configEntry) == False: continue
			if "size"  in configEntry: size  = configEntry["size"]
			if "color" in configEntry: color = configEntry["color"]
			if "style" in configEntry: style = configEntry["style"]
		
		if color == None:
			name = entry["name"]
			if name not in unhandledNames:
				unhandledNames[name] = 0
			unhandledNames[name] += 1
			continue

		# Draw the entity
		drawRect(x, y, size[0], size[1], color=color, style=style)
	print("END DRAW")


	# Draw debug info
	if "displayCenter" in debugFlags:
		print("Center:", imageInfo["center"]["x"], imageInfo["center"]["y"])
		drawCenterRect(
			draw = draw,
			x = imageInfo["center"]["x"] * tileSize + drawCenterX,
			y = imageInfo["center"]["y"] * tileSize + drawCenterY
		)

		drawCenterRect(
			draw = draw,
			x = imageInfo["center"]["x"] * tileSize + drawCenterX,
			y = imageInfo["center"]["y"] * tileSize + drawCenterY,
			width = 25*tileSize,
			height = 25*tileSize,
			isSolid = False
		)

	if "displayZoom" in debugFlags:
		drawCenterRect(
			draw = draw,
			x = imageInfo["center"]["x"] * tileSize + drawCenterX,
			y = imageInfo["center"]["y"] * tileSize + drawCenterY,
			width   = imageInfo["size"]["width"] * tileSize,
			height  = imageInfo["size"]["height"] * tileSize,
			isSolid = False
		)

	# Save the image to a file
	string = config["filename"]
	# string = format_string(string, datetime=timeTxt, surfaceName=surfaceName)
	string = string.format(datetime=timeTxt, surfaceName=surfaceName)
	imagePath = f"images/{string}.png"
	mkdirs( os.path.dirname(imagePath) ) # Make the folders
	image.save(imagePath)  # To save the image as a file
	# outputFiles.append(imagePath)
	print(f"  Surface image saved to {imagePath}")
	print()

	for name in unhandledNames:
		print(f"{name}: {unhandledNames[name]}")


	print("DONE LOADING")


def cleanReset():
	"""
	Clean up all temp files and restart
	"""
	def rm(filePath):
		if os.path.exists(filePath) == False:
			return
		
		if os.path.isdir(filePath):
			shutil.rmtree(filePath)
		else:
			os.remove(filePath)

	rm("factorio"       ) # Factorio server folder
	rm("factorio.tar.xz") # Factorio server download
	rm("lastrun.yaml"   ) # Last run info


""" MAIN ENTRY """
# cleanReset() # Debug
lastRunFilePath = "lastrun.yaml"
startTime = time.time()
tempDirectory = tempfile.TemporaryDirectory()
currentData = None
debugFlags = [
	# "displayZoom", # Renders all collected objects and tiles and shows where the zoom in will be
	# "displayCenter", # Centers the display
]

# Calculate time text
timeObj = datetime.datetime.now()
timeTxt = timeObj.strftime("%Y-%m-%d %H:%M")

# Load our general config file
config = loadConfig()

# Load our shader config file
shaderConfig = loadShaderV1(config["shader"])

# Move our working save to a temp folder to prevent colisions if the user is 
# playing and saving to this file
saveName = config["factorio-save-name"]
if len(saveName) > 4 and saveName[-4:0] == ".zip":
	saveName = saveName[-4:0]

factorioSavePath = os.path.join("/factorio-saves", config["factorio-save-name"] + ".zip")
if os.path.exists(factorioSavePath) == False:
	print(f"ERROR: Save does not exist {factorioSavePath}")
newSavePath = os.path.join(tempDirectory.name, "factorio-save.zip")
shutil.copy(factorioSavePath, newSavePath)
factorioSavePath = newSavePath
del newSavePath

# Check if we need to run the server
useServer = useServer()
print(useServer)
if useServer: collectServerData()

drawImage("aquilo")
drawImage("fulgora")
drawImage("gleba")
drawImage("nauvis")
drawImage("vulcanus")

print("JOB DONE")