# 1. መጀመሪያ Python 3.9 ን እንጭናለን
FROM python:3.9-slim

# 2. በሰርቨሩ ላይ /app የሚባል ፎልደር እንፈጥራለን
WORKDIR /app

# 3. አስፈላጊ የሆኑ ፋይሎችን ወደ ሰርቨሩ ኮፒ እናደርጋለን
COPY requirements.txt .

# 4. ላይብረሪዎቹን (Telebot, Flask, Supabase) እንጭናለን
RUN pip install --no-cache-dir -r requirements.txt

# 5. የቀሩትን የቦቱን ፋይሎች በሙሉ ኮፒ እናደርጋለን
COPY . .

# 6. Render የሚጠቀምበትን የኢንተርኔት በር (Port) እንከፍታለን
EXPOSE 8080

# 7. ቦቱን እና ፍላስክን የሚያስነሳው ትዕዛዝ
CMD ["python", "bot.py"]
