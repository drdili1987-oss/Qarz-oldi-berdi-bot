import codecs

new_keys = {
    'uz': {
        'age_request': 'Yoshingizni kiriting (masalan, 25):',
        'invalid_age': 'Iltimos, faqat to\'g\'ri raqam kiriting (masalan, 25):',
        'gender_request': 'Jinsingizni tanlang:',
        'btn_male': 'Erkak',
        'btn_female': 'Ayol',
        'country_request': 'Qaysi davlatdansiz?',
        'city_request': 'Qaysi shahardansiz?',
        'occupation_request': 'Kasbingiz yoki sohangiz nima? (masalan: Dasturchi, Talaba, Haydovchi...)',
    },
    'ru': {
        'age_request': 'Введите ваш возраст (например, 25):',
        'invalid_age': 'Пожалуйста, введите правильное число (например, 25):',
        'gender_request': 'Выберите ваш пол:',
        'btn_male': 'Мужской',
        'btn_female': 'Женский',
        'country_request': 'Из какой вы страны?',
        'city_request': 'Из какого вы города?',
        'occupation_request': 'Ваша профессия или сфера деятельности? (например: Программист, Студент...)',
    },
    'kk': {
        'age_request': 'Жасыңызды енгізіңіз (мысалы, 25):',
        'invalid_age': 'Дұрыс сан енгізіңіз (мысалы, 25):',
        'gender_request': 'Жынысыңызды таңдаңыз:',
        'btn_male': 'Еркек',
        'btn_female': 'Әйел',
        'country_request': 'Қай елденсіз?',
        'city_request': 'Қай қаладансыз?',
        'occupation_request': 'Кәсібіңіз немесе салаңыз қандай?',
    },
    'en': {
        'age_request': 'Enter your age (e.g., 25):',
        'invalid_age': 'Please enter a valid number (e.g., 25):',
        'gender_request': 'Select your gender:',
        'btn_male': 'Male',
        'btn_female': 'Female',
        'country_request': 'Which country are you from?',
        'city_request': 'Which city are you from?',
        'occupation_request': 'What is your profession or occupation?',
    }
}

with codecs.open('locales/texts.py', 'r', 'utf-8') as f:
    lines = f.readlines()

out = []
current_lang = None

for line in lines:
    out.append(line)
    stripped = line.strip()
    if stripped == '\"uz\": {':
        current_lang = 'uz'
    elif stripped == '\"ru\": {':
        current_lang = 'ru'
    elif stripped == '\"kk\": {':
        current_lang = 'kk'
    elif stripped == '\"en\": {':
        current_lang = 'en'
    
    if current_lang and '\"name_request\"' in line:
        for k, v in new_keys[current_lang].items():
            out.append(f'        \"{k}\": \"{v}\",\n')
        current_lang = None

with codecs.open('locales/texts.py', 'w', 'utf-8') as f:
    f.writelines(out)
print('Texts patched successfully!')
