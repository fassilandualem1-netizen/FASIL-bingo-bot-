# 1. ትንሽ እና ፈጣን የሆነ የፓይዘን ምስል
FROM python:3.10-slim

# 2. የስራ ቦታ (Folder) መፍጠር
WORKDIR /app

# 3. ለፈጣን ስራ የሚያስፈልጉ ሲስተም ላይብረሪዎች
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. requirements.txt መጫን
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. ሁሉንም ፋይሎች ኮፒ ማድረግ
COPY . .

# 6. ፖርት መክፈት
EXPOSE 8080

# 7. ቦቱን ማስነሳት (የፋይሉ ስም bot.py ስለሆነ)
CMD ["python", "bot.py"]
