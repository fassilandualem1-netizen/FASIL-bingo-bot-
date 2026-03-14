# 1. Python መጫን
FROM python:3.9-slim

# 2. የፋይል ማውጫ መፍጠር
WORKDIR /app

# 3. አስፈላጊ ፋይሎችን መቅዳት
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. ሙሉውን ኮድ መቅዳት
COPY . .

# 5. Port መክፈት
EXPOSE 8080

# 6. ቦቱን ማስነሳት (የኮድህ ስም bot.py ከሆነ)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "bot:app"]
