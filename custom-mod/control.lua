function processPlanetChunk(surface, chunkX, chunkY)
	local chunkSize = $$CHUNK_SIZE$$
	local area = {
		{
			-chunkSize + chunkX * chunkSize,
			-chunkSize + chunkY * chunkSize
		},
		{
			chunkSize + chunkX * chunkSize,
			chunkSize + chunkY * chunkSize
		}
	}
	local entities = game.surfaces[surface].find_entities(area)
	
	local exportTiles = {}

	for x = area[1][1], area[2][1], 1 do
		for y = area[1][2], area[2][2], 1 do
			local tile = game.surfaces[surface].get_tile(x, y)
			-- Skip nil tiles
			if tile.valid then
				local exportTile = {
						name = tile.name,
						x = tile.position.x,
						y = tile.position.y,
						type = "TILE"
				}
				table.insert(exportTiles, exportTile)
			end
		end
	end


	local exportEntities = {}
	for _, entity in pairs(entities) do
		-- print(entity.name) -- This will print the name of each entity
		local exportEntity = {
			name = entity.name,
			x = entity.position.x,
			y = entity.position.y,
			type = "ENTITY"
		}
		table.insert(exportEntities, exportEntity)
	end

	-- print(helpers.table_to_json(entities))
	local data = {
		hello = "world",
		entities = exportEntities,
		tiles = exportTiles
	}


	filePath = string.format("%s/%dx%d.json", surface, chunkX, chunkY)
	helpers.write_file(filePath,
		helpers.table_to_json(data),
		false, 0
	)
end


script.on_init(function()
	-- Your initialization code here
	print("b8VmXhHtuENCBh6q")

	-- Loop though every planet and run the process function on them
	for planetName, planet in pairs(game.planets) do
		-- processPlanetChunk(planetName, 0, 0)
		-- print(planetName)
		size = $$SCAN_RANGE$$ -- Set a range for us to scan via python
		for x = -size, size, 1 do
			for y = -size, size, 1 do
				processPlanetChunk(planetName, x, y)
			end
		end
		print(planetName) -- Print the name for python to process this planet
	end

	-- local planetName = "nauvis"
	-- size = $$SCAN_RANGE$$
	-- for x = -size, size, 1 do
	-- 	for y = -size, size, 1 do
	-- 		processPlanetChunk(planetName, x, y)
	-- 	end
	-- end
	-- print(planetName)

	-- Crash the game
	-- print("JOB DONE")
	helpers.print("AHH A CRASH")
end)