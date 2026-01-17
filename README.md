# Factorio Map Creator
A tool for turning Factorio maps in to pictures. Allows you to configure custom image ratios, colors, included structures, etc. Currently only compatiable with Linux due to the server files.

**Does not currently do ships.**

Inspired by [Drawscape Factorio](https://github.com/drawscape-labs/drawscape-factorio).

# Docker Installation
Build the container with `docker build -t factorio-plot:local .`

Run the container with `docker compose up`

You can edit the factorio save location in the `compose.yaml` file.


# Customization
The customization is done using the `config.yaml` and a shaders `.yaml` file. Please see below for more information.

## config.yaml
The `config.yaml` file allows you to edit to edit all of the below details.

<ins>aspect-ratio</ins> **required**<br/>
The desired aspect ratio for the generated images. Can be any number, including decibles. In this format: `width:height`.

<ins>padding</ins><br/>
Can be set to either px or %, and any numerical value is valid.

<ins>shader</ins> **required**<br/>
Lets you select your desired shader file. This project provides several defaults to pick from, or you can make your own. See more in the shader.yaml section below.

<ins>filename</ins> **required**<br/>
The name format for the generated images. You can use `{datetime}` and `{surfaceName}`. This acts as creating a path, so you will want to avoid slashes unless you are wanting them stored in a folder.

<ins>auto-update-server</ins> **required**<br/>
When set to true, it will automatically download the newest Factorio server from their website and will use it to create the files. This is primarily for if someone is using an older version of Factorio and is unable to update.

<ins>factorio-save-name</ins> **required**<br/>
Name of the Factorio save in the save path directory. You do not need to include the `.zip`.

<ins>factorio-save-path</ins> **required**<br/>
The location of the save file.

<ins>backgrounds-folder</ins><br/>
Where the files are moved to if you do not want them to be in the default `images` folder.

<ins>auto-generated</ins><br/>
A flag to show whether or not you want the script's tutorial messages.

## Shaders
The shader file is broken up into several parts. There are some details below. For more in-depth examples, please see the provided shader configs within the `shaders` folder.

### Group
Here you can create your own custom groups. You name the group, list the assets, and set the scope of the group. Please see the example and explanation below.

```
group: <- Unchangeable
  basicGroup: <- Set to desired identifier
    names: [assembling-machine, inserter]
    func: IN
```

- The group name--in this case "basicGroup"--should be set to whatever identifier you want.
- `names` are the asset names you want to add to this group. Dev does not currently have this available, and your best bet would be to look at the example shader files provided.
- `func` can be set to either EXACT or IN. EXACT means one of the asset names must perfectly match, and IN just makes sure it contains one of the names.


### Styles
This section of the shader yaml files allow you to create the default styling for the images. You can use the groups you defined above, or write using the names and func variables just like in groups. The basic format is as follows:

```
planets: <- Unchangable
  planetName: <- name of planet you want to apply the styling to
    - group: nameOfGroup
      color: "colorYouWant"
  planetName2:  <- name of planet you want to apply the styling to
    - names: [assembling-machine, inserter]
      func: IN
      color: "colorYouWant"
```