# Download tessconfigs folder
git clone https://github.com/tesseract-ocr/tessconfigs.git
# Build Docker image containing Tesseract
set -e
docker build -t tess_layer -f Dockerfile-tess4 .
# Copy Tesseract locally
CONTAINER=$(docker run -d tess_layer false)
docker cp $CONTAINER:/opt/build-dist layer
docker rm $CONTAINER
# Zip Tesseract
cd layer/
zip -r ../tesseract-layer.zip .
# Clean
cd ..
rm -rf layer/
rm -rf tessconfigs/
