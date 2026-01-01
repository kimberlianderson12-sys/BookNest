# Инструкция: Загрузка проекта BookNest в GitHub

## Вариант 1: Если репозиторий уже существует на GitHub

### Шаг 1: Удалить текущий remote (если есть проблемы)

```bash
git remote remove origin
```

### Шаг 2: Добавить все файлы в Git

```bash
# Добавить все файлы
git add .

# Проверить статус
git status
```

### Шаг 3: Создать коммит (если есть изменения)

```bash
git commit -m "feat: Полная версия проекта BookNest с мобильной адаптивностью"
```

### Шаг 4: Добавить remote репозиторий

```bash
git remote add origin https://github.com/kimberlianderson12-sys/BookNest.git
```

### Шаг 5: Отправить в GitHub (принудительно, если нужно)

```bash
# Обычный push
git push -u origin main

# ИЛИ если нужно перезаписать (ОСТОРОЖНО!)
git push -u origin main --force
```

---

## Вариант 2: Создание нового репозитория на GitHub

### Шаг 1: Создать репозиторий на GitHub

1. Зайдите на https://github.com
2. Нажмите кнопку **"+"** в правом верхнем углу
3. Выберите **"New repository"**
4. Заполните:
   - **Repository name:** `BookNest`
   - **Description:** `Система управления библиотекой`
   - **Visibility:** Public или Private (на ваше усмотрение)
   - **НЕ** ставьте галочки на "Add a README file", "Add .gitignore", "Choose a license"
5. Нажмите **"Create repository"**

### Шаг 2: В локальной папке проекта

```bash
# Убедитесь, что вы в папке проекта
cd C:\BookNest

# Инициализируйте Git (если еще не инициализирован)
git init

# Добавьте все файлы
git add .

# Создайте первый коммит
git commit -m "feat: Начальная версия проекта BookNest"

# Добавьте remote репозиторий (замените URL на ваш)
git remote add origin https://github.com/kimberlianderson12-sys/BookNest.git

# Отправьте код
git branch -M main
git push -u origin main
```

---

## Вариант 3: Полный сброс и загрузка заново

### Шаг 1: Удалить все связи с GitHub

```bash
# Удалить remote
git remote remove origin

# Удалить все коммиты (опционально, если хотите начать с чистого листа)
# ВНИМАНИЕ: Это удалит всю историю!
rm -rf .git
git init
```

### Шаг 2: Добавить все файлы

```bash
git add .
git commit -m "feat: Проект BookNest - система управления библиотекой"
```

### Шаг 3: Подключить к GitHub

```bash
git remote add origin https://github.com/kimberlianderson12-sys/BookNest.git
git branch -M main
git push -u origin main --force
```

---

## Быстрая команда (если репозиторий уже создан на GitHub)

```bash
# Удалить старый remote
git remote remove origin

# Добавить новый
git remote add origin https://github.com/kimberlianderson12-sys/BookNest.git

# Добавить все файлы
git add .

# Коммит
git commit -m "feat: Проект BookNest"

# Отправить
git push -u origin main --force
```

---

## Проверка

После загрузки проверьте:

```bash
# Проверить remote
git remote -v

# Проверить статус
git status

# Посмотреть последние коммиты
git log --oneline -5
```

---

## Если возникают ошибки

### Ошибка: "remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/kimberlianderson12-sys/BookNest.git
```

### Ошибка: "failed to push some refs"
```bash
# Сначала получить изменения
git pull origin main --allow-unrelated-histories

# Затем отправить
git push -u origin main
```

### Ошибка: "authentication failed"
- Проверьте, что вы авторизованы в Git
- Может потребоваться Personal Access Token вместо пароля

---

## Важно!

- `--force` перезаписывает историю на GitHub - используйте осторожно!
- Убедитесь, что важные данные не потеряются
- Перед `--force` лучше сделать backup

