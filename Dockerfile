# የ Python ስሪት
FROM python:3.9-slim

# በኮንቴይነሩ ውስጥ ፋይሎች የሚቀመጡበት ቦታ
WORKDIR /app

# አስፈላጊ የሆኑ ፋይሎችን መቅዳት
COPY requirements.txt .

# ላይብረሪዎችን መጫን
RUN pip install --no-cache-dir -r requirements.txt

# ሙሉውን ኮድ መቅዳት
COPY . .

# ቦቱን ማስነሳት
CMD ["python", "bot.py"]
