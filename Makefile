chunkslocation := chunks.txt

runalpinetest:
	docker build . -f testing/Dockerfile -t ribs/ribs 
	docker run -v $(chunkslocation):/chunks.txt ribs/ribs