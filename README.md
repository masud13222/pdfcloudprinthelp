# PDF হেল্পার টেলিগ্রাম বট

এই বটটি PDF ফাইল নিয়ে কাজ করার জন্য তৈরি করা হয়েছে। এর মাধ্যমে আপনি একাধিক PDF ফাইল একত্রিত করতে পারবেন, PDF পেজ ইনভার্ট করতে পারবেন, এবং আরও অনেক কিছু করতে পারবেন।

## প্রধান ফিচারসমূহ

### ব্যবহারকারী কমান্ডসমূহ
- `/start` - বট শুরু করুন এবং স্বাগত বার্তা দেখুন
- `/merge <number>` - একাধিক PDF ফাইল একত্রিত করুন
- `/allcancel` - সকল চলমান কমান্ড বাতিল করুন
- `/invert` - একটি PDF ফাইলের পেজগুলি উল্টো করুন
- `/inverts` - একাধিক PDF ফাইলের পেজগুলি উল্টো করুন
- `/pdf` - Google Drive লিংক থেকে PDF ডাউনলোড করুন
- `/price` - মূল্য হিসাব করুন
- `/pages` - PDF এর পেজ সংখ্যা দেখুন

### এডমিন কমান্ডসমূহ
- `/users` - মোট ব্যবহারকারীর সংখ্যা এবং তথ্য দেখুন
- `/broadcast` - সকল ব্যবহারকারীদের কাছে মেসেজ পাঠান
- `/uset` - বট সেটিংস পরিবর্তন করুন
- `/groupon` - গ্রুপে বট সক্রিয় করুন
- `/groupoff` - গ্রুপে বট নিষ্ক্রিয় করুন

## সেটআপ নির্দেশনা

1. প্রথমে প্রয়োজনীয় প্যাকেজগুলি ইনস্টল করুন:
```bash
pip install -r requirements.txt
```

2. `.env` ফাইলে নিম্নলিখিত তথ্যগুলি সেট করুন:
```env
BOT_TOKEN=আপনার_বট_টোকেন
MONGODB_URI=আপনার_মঙ্গোডিবি_ইউআরআই
DB_NAME=pdf_helper_bot
ADMIN_IDS=আপনার_টেলিগ্রাম_আইডি
API_ID=টেলিগ্রাম_এপিআই_আইডি
API_HASH=টেলিগ্রাম_এপিআই_হ্যাশ
FORCE_SUB_CHANNEL=আপনার_চ্যানেল_ইউজারনেম
```

3. বট চালু করুন:
```bash
python bot.py
```

### Heroku Deploy
```bash
# ফাইল এড করুন
git add .

# কমিট করুন
git commit -m "All OK"

# হেরোকুতে পুশ করুন
git push heroku main

# ওয়ার্কার প্রসেস স্কেল করুন
heroku ps:scale worker=1
```

## বিস্তারিত ব্যবহার নির্দেশিকা

### PDF মার্জ করা
1. `/merge <number>` কমান্ড দিন (যেমন: `/merge 3`)
2. বট যখন চাইবে তখন PDF ফাইলগুলি একে একে পাঠান
3. সব PDF পাঠানো হলে, বট একটি মার্জ করা PDF ফাইল পাঠিয়ে দিবে

### PDF ইনভার্ট করা
1. `/invert` কমান্ড দিন
2. একটি PDF ফাইল পাঠান
3. বট PDF এর পেজগুলি উল্টিয়ে নতুন PDF পাঠিয়ে দিবে

### গ্রুপ ফিচারসমূহ
- স্বয়ংক্রিয় স্বাগত বার্তা
- লিংক ফিল্টারিং
- সার্ভিস মেসেজ ডিলিট
- কাস্টম WhatsApp এবং ফোন নম্বর বাটন

### এডমিন প্যানেল
- ব্যবহারকারী পরিসংখ্যান
- ব্রডকাস্ট মেসেজিং
- গ্রুপ সেটিংস কনফিগারেশন
- স্বাগত বার্তা কাস্টমাইজেশন

## প্রয়োজনীয়তা

- Python 3.7+
- MongoDB ডাটাবেস
- টেলিগ্রাম বট টোকেন
- টেলিগ্রাম API ক্রেডেনশিয়ালস

## সতর্কতা
- বটের সাথে সবসময় সঠিক ফরম্যাটে PDF ফাইল পাঠান
- বড় সাইজের PDF ফাইল প্রসেস করতে কিছু সময় লাগতে পারে
- একবারে খুব বেশি সংখ্যক PDF মার্জ করার চেষ্টা করবেন না

## সাপোর্ট
যদি কোন সমস্যা হয় বা সাহায্য লাগে, আমাদের টেলিগ্রাম চ্যানেলে যোগ দিন। 
