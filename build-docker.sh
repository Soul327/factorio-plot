# docker build -t factorio-plot .

docker run -it --rm -v "$HOME/.factorio/saves":/factorio-saves -v "$(pwd)":/app factorio-plot