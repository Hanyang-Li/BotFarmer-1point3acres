mkdir /app/src/tesstrain/data
unzip /app/ground-truth.zip -d /app/src/tesstrain/data > /dev/null 2>&1
cd /app/src/tesstrain/data
mv ground-truth $1-ground-truth
tail -f /dev/null