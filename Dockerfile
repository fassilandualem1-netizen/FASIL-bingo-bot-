# 1. የፓይዘን ቤዝ ምስል
FROM python:3.10-slim

# 2. በሰርቨሩ ውስጥ የሚሰራበት ፎልደር
WORKDIR /app

# 3. አስፈላጊ ፋይሎችን ወደ ሰርቨሩ መቅዳት
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 4. ቦቱን ማስነሻ ትዕዛዝ
CMD ["python", "bot.py"]
