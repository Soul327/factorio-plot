import hashlib, math, os

""" UTILITY FUNCTIONS """
def getRunType():
	"""
	Get the run type of the system.
	Options include
	 - windows
	 - linux
	 - nixos
	 - unknown
	"""
	if platform.system() == "Windows":
		return "windows"
	
	if platform.system() == "Linux":
		if "NixOS" in platform.version():
			return "nixos"
		return "linux"
	# print(platform.system())
	# print(platform.version())
	return "unknown"


def format_string(s, **kwargs):
	return s.format(**kwargs)


def mkdirs(directory_path):
	try:
		os.makedirs(directory_path)
	except FileExistsError:
		pass


def unixDurationToText(unix_seconds):
	"""
	Converts a unix time int to a human readable string
	"""
	seconds = unix_seconds
	minutes = unix_seconds/60
	hours = minutes/60
	days = hours/24
	years = days/365

	text = ""

	if hours >= 1: text += f"{hours:<.0f} hours & "
	if minutes >= 1 and days < 1:
		num = (hours % 1) * 60
		text += f"{num:<.0f} minutes & "
	if seconds >= 1 and hours < 1:
		num = (minutes % 1) * 60
		text += f"{num:<.0f} seconds & "
	return text[0:-3]


def match(entity, colorCode):
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


def getAspect(width, height):
	"""
	Grabs the aspect ratio of the screen
	"""
	width = int(width)
	height = int(height)
	# Calculate the greatest common divisor of the width and height
	gcd_value = math.gcd(width, height)

	# Simplify the aspect ratio
	aspect_ratio_width = width // gcd_value
	aspect_ratio_height = height // gcd_value

	return aspect_ratio_width, aspect_ratio_height


def getFileHash(filePath):
	algorithm = 'sha256'
	func = hashlib.new(algorithm)
	
	with open(filePath, 'rb') as f:
		while chunk := f.read(8192):
			func.update(chunk)
					
	return func.hexdigest()


