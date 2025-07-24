import time, json, os, yaml, statistics, math, subprocess, threading, shutil, sys, platform, requests
import tarfile
from datetime import datetime
from PIL import Image, ImageDraw
import time
import argparse
import platform
import utils

class LoadingManager:
	def __init__(self, text):
		self.text = text
		self.isLoading = False
		self.index = 0
		self.loadingChars = ["-", "\\", "|", "/"]
		self.thread = None
		self.start()

	def worker(self):
		while self.isLoading:
			print(f"\r{self.text}{self.loadingChars[self.index]}", end="", flush=True)
			self.index += 1
			time.sleep(.1)
			if self.index > len(self.loadingChars) - 1:
				self.index = 0
		print(f"\r{self.text} done.")
	
	def start(self):
		self.isLoading = True

		self.thread = threading.Thread(target=self.worker, daemon=True)
		self.thread.start()
	
	def stop(self):
		self.isLoading = False
		self.thread.join()


def drawSurface(surfaceName, localSurfaceConfig):
	"""
	Draws the given surface on to an image
	"""
	def drawRect(x, y, width=1, height=1, color = 'red', style = "solid"):
		nonlocal tileSize, draw, imageWidth, imageHeight

		# Make the center of the image 0, 0
		x -= (width /2)
		y -= (height/2)

		x -= imageCenterX
		y -= imageCenterY

		# Define the box parameters
		top_left = (
			(x*tileSize) + (imageWidth/2), 
			(y*tileSize) + (imageHeight/2) - (width/2)
		) # Starting point (x, y)
		box_size = (tileSize*width, tileSize*height)  # Width and height (width, height)

		# Out of the image
		if top_left[0] < 0 or top_left[1] < 0: return
		if box_size[0] > imageWidth or box_size[1] > imageHeight: return

		# Draw the red box
		cords = [top_left, (top_left[0] + box_size[0], top_left[1] + box_size[1])]
		match style:
			case "solid": draw.rectangle(cords, fill=color, outline=color)
			case "outline": draw.rectangle(cords, outline=color, width=2)

	print(f"Drawing surface {surfaceName}...")

	# Store unhandled names and tiles to make life easier for the localSurfaceConfig writers
	unhandledNames = {}

	# Load our surface data & combine
	bigData = {
		"entities": [],
		"tiles": []
	}
	print("  Loading script export file...", end="", flush=True)
	scriptOutput = "factorio/script-output"
	for file in os.listdir(scriptOutput):
		# Skip non matching
		if file.startswith(surfaceName) == False:
			continue

		# Process matching
		filePath = f"{scriptOutput}/{file}"
		# print(f"Processing {filePath}")
		with open(filePath, 'r') as file:
			data = json.load(file)

			if "entities" in data:
				bigData["entities"] += data["entities"]
			
			if "tiles" in data:
				bigData["tiles"] += data["tiles"]
	data = bigData
			
	print(" done.")

	tileSize = 5
	imageCenterX, imageCenterY = 0, 0
	imageWidth  = tileSize * int(2000/2) # Default size
	imageHeight = tileSize * int(2000/2) # Default size

	# Grab all of the cords for use in image center, scale and scope
	print("  Finding scope of surface...", end="", flush=True)
	xCords, yCords = [], []
	for entry in data["entities"]:
		for localSurfaceConfigEntry in localSurfaceConfig["entries"]:
			if utils.match(entry, localSurfaceConfigEntry) == False: continue
			if "flags" not in localSurfaceConfigEntry: continue
			if "center" not in localSurfaceConfigEntry["flags"]: continue # Make sure that this preset has the center flag
			xCords.append(entry["x"])
			yCords.append(entry["y"])
	print(" done.")

	# Check if there is things to put on the image
	if xCords == [] or yCords == []:
		print("Planet has nothing on it")
		return

	# Move the image center, scale and scope
	# Get the image center
	minx, maxx = min(xCords), max(xCords)
	miny, maxy = min(yCords), max(yCords)
	imageCenterX = (maxx+minx) / 2
	imageCenterY = (maxy+miny) / 2

	# Get the image bounds
	# print(f"  Image Center: ({imageCenterX}, {imageCenterY})")

	# Find the min and max of our image
	tileWidth  = abs(minx) + abs(maxx)
	tileHeight = abs(miny) + abs(maxy)

	# print(f"  X RANGE: ({minx}, {maxx})")
	# print(f"  Y RANGE: ({miny}, {maxy})")

	tileWidth  = int(tileWidth )
	tileHeight = int(tileHeight)

	imageAreaWidth  = int(tileWidth  * tileSize)
	imageAreaHeight = int(tileHeight * tileSize)

	imageWidth  = imageAreaWidth
	imageHeight = imageAreaHeight

	# Grab the padding
	hasError = False
	try:
		padding = config["padding"]
		
		if "%" in padding:
			padding = padding[0:-1]
			mult = 1+(float(padding) / 100)
			imageWidth *= mult
			imageHeight *= mult
		elif "px" in padding:
			padding = float(padding[0:-2])
			imageWidth += padding
			imageHeight += padding
		else:
			hasError = True
	except:
		hasError = True

	if hasError:
		print(f"ERROR: Unknown padding format: {padding}. Try 10% or 10px next time.")


	# Merge tiles and entities in to one array
	entries = data["tiles"] + data["entities"]
	del data

	# Alter the image width and height to fit our aspect ratio
	if "aspect-ratio" in config:
		# print("  Updating aspect ratio")
		try:
			# Break our the ratio in to two strings
			ratio = config["aspect-ratio"]
			if ":" in config["aspect-ratio"]:
				expectedW, expectedY = ratio.split(":")
			elif "x" in config["aspect-ratio"]:
				expectedW, expectedY = ratio.split("x")

			# Make the strings into numbers
			expectedW, expectedY = float(expectedW), float(expectedY)
			# print(f"    New ratio: ({expectedW}:{expectedY})")
		except:
			print(f"Error processing:'aspect-ratio: \"{ratio}\"'\tCorrect Example: 'aspect-ratio: \"16:9\"'")
			exit()


		# imageWidth, imageHeight = int(imageWidth), int(imageHeight)
		# print(f"    Current image size: ({imageWidth}:{imageHeight})")
		w, h = utils.getAspect(imageWidth, imageHeight)
		if w != expectedW and h != expectedY:
			# Create two options
			newWidth = imageHeight * (expectedW/expectedY)
			newHeight = (expectedY*imageWidth)/expectedW

			if newWidth  > imageWidth : imageWidth  = newWidth
			if newHeight > imageHeight: imageHeight = newHeight
		# print(f"    New image size: ({imageWidth}:{imageHeight})")

	# Create our image
	backgroundColor = (0, 0, 0, 0)
	if "background-color" in localSurfaceConfig:
		backgroundColor = localSurfaceConfig["background-color"]
		print("BACKGROUND COLOR", backgroundColor)
	imageWidth, imageHeight = int(imageWidth), int(imageHeight)
	image = Image.new('RGBA', (imageWidth, imageHeight), backgroundColor) # Create a new image with a white background
	draw = ImageDraw.Draw(image) # Create a drawing context



	# Draw entities to our image
	drawCount = 0
	lm = LoadingManager("  Drawing image...")
	for entry in entries:
		name = entry["name"]

		# Set/load default values
		color = None
		style = "solid"
		size = (1, 1)
		x, y = entry["x"], entry["y"]

		# Skip this entry if its not in range of the drawn image
		# TODO var/2 is not correct and is over reaching, find the correct formula
		if x/2 < minx: continue
		if x/2 > maxx: continue
		if y/2 < miny: continue
		if y/2 > maxy: continue

		for localSurfaceConfigEntry in localSurfaceConfig["entries"]:
			# Make sure that this localSurfaceConfig matches this planet
			if len(localSurfaceConfigEntry["planets"]) > 0:
				if surfaceName not in localSurfaceConfigEntry["planets"]:
					continue
			
			if utils.match(entry, localSurfaceConfigEntry) == False: continue
			if "size"  in localSurfaceConfigEntry: size  = localSurfaceConfigEntry["size"]
			if "color" in localSurfaceConfigEntry: color = localSurfaceConfigEntry["color"]
			if "style" in localSurfaceConfigEntry: style = localSurfaceConfigEntry["style"]
		
		if color == None:
			name = entry["name"]
			if name not in unhandledNames:
				unhandledNames[name] = 0
			unhandledNames[name] += 1
			continue # No color no draw
		# print(f"DRAW {name} Location: ({size[0]}, {size[1]}) Color: {color} Size: {size} Style: {style}")
		drawRect(entry["x"], entry["y"], size[0], size[1], color=color, style=style)
		drawCount += 1
		lm.text = f"  Drawing image {drawCount}..."

	lm.stop()



	# Sort our names
	unhandledNames = dict(sorted(unhandledNames.items(), key=lambda item: item[1]))

	# Print out unhandled entries
	# for name in unhandledNames:
	# 	print(f"  Unhandled entry: {name} ({unhandledNames[name]})")


	# Save the image or show it
	x = (imageWidth /2) - (imageAreaWidth /2)
	y = (imageHeight/2) - (imageAreaHeight/2)
	width  = imageAreaWidth 
	height = imageAreaHeight

	# Draw required draw area
	# draw.rectangle([(x, y), (x+width, y+height)], outline="red", width=2)

	string = config["filename"]
	string = utils.format_string(string, datetime=timeTxt, surfaceName=surfaceName)
	imagePath = f"images/{string}.png"
	utils.mkdirs( os.path.dirname(imagePath) ) # Make the folders
	image.save(imagePath)  # To save the image as a file
	outputFiles.append(imagePath)
	print(f"  Surface image saved to {imagePath}")
	print()


def loadShaderV1(shaderFile = None, debug = False):
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

	if debug:
		print(f"\nConfigs:")
		for configEntry in newConfig:
			print(" ", configEntry)
	return newConfig


def workerThread():
	"""
	Waits for jobs from the server
	"""
	while running and len(jobs) <= 0:
		time.sleep(1/20)
		if len(jobs) <= 0: continue

		filename = jobs.pop(0)
		drawSurface(filename, shaderConfig)


def updateServer():
	"""
	Pulls the latest server from wube
	"""
	print("Checking server...")
	url = "https://factorio.com/get-download/stable/headless/linux64"  # Server download URL
	output_path = "factorio.tar.xz"  # Server download path
	
	isServerUpToDate = False
	if os.path.exists(output_path):
		lastServerUpdate = os.stat(output_path).st_mtime
		if time.time() - lastServerUpdate < 86400:
			print("  Server is up to date\n")
			isServerUpToDate = True

	if isServerUpToDate == False:
		# Download the new server
		lm = LoadingManager("  Downloading new server...")
		response = requests.get(url) # Send a GET request to the URL
		if response.status_code != 200: # Check if the request was successful
			print("Response from server {url} was unsuccessfull, the server maybe old")
			return
			
		# Open the output file and write the content of the response to it
		with open(output_path, 'wb') as f:
			f.write(response.content)
		lm.stop()

		# Delete the old server 
		factorioServerPath = "factorio"
		if os.path.exists(factorioServerPath) and os.path.isdir(factorioServerPath):
			print("  Removing old server path...", end="", flush=True)
			shutil.rmtree(factorioServerPath)
			print(" done.")

	# Extract the new server
	lm = LoadingManager("  Extracting server file...")
	with tarfile.open("factorio.tar.xz", "r") as tar:
		tar.extractall(path=".", filter='fully_trusted')
	lm.stop()

	print("  Moving mod...", end="", flush=True)
	if os.path.exists("factorio/mods") == False:
		os.mkdir("factorio/mods")
	updateMod()
	print(" done.")

	print() # Func done


def updateMod():
	"""
	Copies our mod to our Factorio server and update variables based on the config
	file
	"""

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


def createImages(config):
	"""
	Creates backgrounds for each of the planets exported with the custom mod using
	a single thread 
	"""
	# Get a list of the planets
	uniqueSurfaces = []
	for filename in os.listdir("factorio/script-output"):
		# Omit the chunk cords
		surfaceName = filename[0:filename.rfind(' (')]

		# Only run each planet once
		if surfaceName in uniqueSurfaces: continue
		uniqueSurfaces.append(surfaceName)
	
	# Create images for each
	for surfaceName in uniqueSurfaces:
		startTime = time.time()

		filename = filename[0:-5]
		drawSurface(surfaceName, config)

		endTime = time.time()
		deltaTime = endTime - startTime
		timeString = utils.unixDurationToText(deltaTime)
		print(f"Planet done in {timeString}\n")


def startServer():
	"""
	Runs the Factorio server
	"""
	# Empty our server output
	scriptOutputPath = "factorio/script-output"
	if os.path.exists(scriptOutputPath):
		shutil.rmtree(scriptOutputPath)

	# Remove lock file
	lockFilePath = "factorio/.lock"
	if os.path.exists(lockFilePath):
		print("Removing server lockfile")
		os.remove(lockFilePath)

	# Run the command and get updates from its standard output
	# print("Starting Factorio server")
	lm = LoadingManager("Starting Factorio server...")
	command = ["factorio/bin/x64/factorio", "--start-server", "factorio-save/"+config["factorio-save-name"], "--server-settings", "server-settings.json"]
	# print(" ".join(command)) # Print out the command used to run the server
	p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	totalOutput = ""

	flagModLines = False
	modIndicator = "b8VmXhHtuENCBh6q" # The line the indicate that the mod is in control, further lines will be output from the mod

	while True:
		output_data = p.stdout.read(1) # Receive 1024 bytes of data from the pipe at a time
		
		if not output_data: break
		
		# Decode the output from bytes to string
		output_str = output_data.decode('utf-8')
		totalOutput += output_str

		if modIndicator in totalOutput:
			totalOutput = totalOutput[totalOutput.index(modIndicator)+len(modIndicator)+2:]
			flagModLines = True
			lm.stop()
			print("Waiting for server to finish collecting data...\n")
		
		if flagModLines and "\n" in totalOutput:
			line = totalOutput[0:totalOutput.index("\n")]
			totalOutput = totalOutput[totalOutput.index("\n")+2:]
			if "Error ServerMultiplayerManager.cpp" in line: break
			if modIndicator not in line and len(line.strip()) > 0:
				# print(f"Line: {line}")
				jobs.append(line)

	# Wait for the command to finish and get its final standard error
	final_output, final_error = p.communicate()

	if final_error:
		print(f"Error: {final_error.decode('utf-8')}")

	# Write info about this run to the last run file
	with open(lrFilePath, 'w') as file:
		yaml.dump({
			"save-hash": saveFileHash
		}, file, default_flow_style=False)


def processCommand():
	"""
	Processes the command arguments
	"""
	# Initialize parser
	parser = argparse.ArgumentParser()

	# Adding optional argument
	parser.add_argument("-i", "--input-path" , help = "The Factorio save input file")
	parser.add_argument("-o", "--output-path", help = "Sets the output directory for the image files")

	# Read arguments from command line
	args = parser.parse_args()

	if args.input_path:
		directory = os.path.dirname(args.input_path)
		filename = os.path.basename(args.input_path)

		# Remove .zip
		if filename[-4:] == ".zip":
			filename = filename[:-4]
		
		configOverride["factorio-save-path"] = directory
		configOverride["factorio-save-name"] = filename

	if args.output_path:
		configOverride["backgrounds-folder"] = args.output_path


""" MAIN ENTRY """
startTime = time.time()

debug = False
running = True
jobs = [] # Stored jobs for the worker thread
outputFiles = [] # Paths to the output images
configOverride = {} # Overrides for the config file set by the commands

processCommand()

# Load our general config file
if os.path.exists('config.yaml') == False:
	shutil.copy('config-example.yaml', 'config.yaml')

with open('config.yaml', 'r') as f:
	config = yaml.safe_load(f)
config = {**config, **configOverride}

print(config)

if "auto-generated" in config and config["auto-generated"] == True:
	print("Please verify in config.yaml that the settings are correct. Then change auto-generated to False and run again.")
	exit()

shaderConfig = loadShaderV1(config["shader"])


# Calculate time text
timeObj = datetime.now()
timeTxt = timeObj.strftime("%Y-%m-%d %H:%M")


# Copy our save
if "factorio-save-path" in config:
	# Make sure our copy dst exists
	tmpSaveFolder = "factorio-save"
	if not os.path.exists(tmpSaveFolder):
		os.makedirs(tmpSaveFolder)

	# Move our files
	factorioSavePath = os.path.expanduser( config["factorio-save-path"] + "/" + config["factorio-save-name"] + ".zip" )
	if os.path.exists(factorioSavePath) == False:
		print(f"Looking for save at {factorioSavePath}\nThe save '{config['factorio-save-name']}' does not exist in the directory '{config['factorio-save-path']}'. Exiting")
		exit()
	print(f"Copying our Factorio save file '{factorioSavePath}'")
	shutil.copy(factorioSavePath, tmpSaveFolder+"/")
localSavePath = f"factorio-save/{config['factorio-save-name']}.zip"


# Check if this save has already ran (no need to fetch new)
useServer = True # Run the server to generate the map
lrFilePath = "lastrun.yaml"
saveFileHash = utils.getFileHash(localSavePath)
if os.path.exists(lrFilePath):
	with open(lrFilePath, 'r') as file:
		data = yaml.safe_load(file)
	
	# Save file has not changed since the last run, no need for server
	if data["save-hash"] == saveFileHash:
		useServer = False

if os.path.exists("factorio/script-output") == False:
	useServer = True

# Create our images
print()
if useServer:
	updateMod()
	updateServer()

	# Creating worker thread
	workerThread = threading.Thread(target=workerThread, daemon=True)
	workerThread.start()

	# Start the server to gather data
	startServer()

	running = False # Signal the worker thread to stop
	workerThread.join()
else:
	createImages(shaderConfig)



# Copy our output images to the background folder
if "backgrounds-folder" in config:
	backgroundFolder = os.path.expanduser( config["backgrounds-folder"] )
	print(f"Copying our images to '{backgroundFolder}'")
	for entry in outputFiles:
		shutil.copy(entry, backgroundFolder)



endTime = time.time()
deltaTime = endTime - startTime
timeString = utils.unixDurationToText(deltaTime)
print(f"Job done in {timeString}")