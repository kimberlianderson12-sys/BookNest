-- УДАЛЯЕМ ВСЕ ТАБЛИЦЫ
DROP TABLE IF EXISTS reservations CASCADE;
DROP TABLE IF EXISTS book_copies CASCADE;
DROP TABLE IF EXISTS book_genres CASCADE;
DROP TABLE IF EXISTS book_authors CASCADE;
DROP TABLE IF EXISTS books CASCADE;
DROP TABLE IF EXISTS genres CASCADE;
DROP TABLE IF EXISTS authors CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. ПОЛЬЗОВАТЕЛИ (users.xlsx)
CREATE TABLE users (
    username VARCHAR(50) PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20),
    card_number VARCHAR(20) UNIQUE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('reader', 'librarian', 'admin')),
    max_books INTEGER DEFAULT 5,
    password VARCHAR(50) NOT NULL
);

-- 2. АВТОРЫ (authors.xlsx)
CREATE TABLE authors (
    author_id INTEGER PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    birth_year INTEGER,
    death_year INTEGER,
    bio TEXT
);

-- 3. ЖАНРЫ (genres.xlsx)
CREATE TABLE genres (
    genre_id INTEGER PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    parent_id INTEGER
);

-- 4. КНИГИ (books.xlsx)
CREATE TABLE books (
    book_id INTEGER PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    isbn VARCHAR(20),
    publication_year INTEGER,
    publisher VARCHAR(200),
    pages INTEGER,
    language VARCHAR(50) DEFAULT 'Русский',
    description TEXT
);

-- 5. СВЯЗЬ КНИГИ-АВТОРЫ (book_authors.xlsx)
CREATE TABLE book_authors (
    book_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    PRIMARY KEY (book_id, author_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES authors(author_id) ON DELETE CASCADE
);

-- 6. СВЯЗЬ КНИГИ-ЖАНРЫ (book_genres.xlsx)
CREATE TABLE book_genres (
    book_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (book_id, genre_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(genre_id) ON DELETE CASCADE
);

-- 7. ЭКЗЕМПЛЯРЫ КНИГ (book_copies.xlsx)
CREATE TABLE book_copies (
    copy_id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL,
    inventory_number VARCHAR(50) UNIQUE NOT NULL,
    condition VARCHAR(20) CHECK (condition IN ('new', 'good', 'fair', 'poor')),
    status VARCHAR(20) DEFAULT 'available' CHECK (status IN ('available', 'reserved', 'issued', 'lost')),
    location VARCHAR(100),
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE
);

-- 8. БРОНИРОВАНИЯ (reservations.xlsx)
CREATE TABLE reservations (
    copy_id INTEGER NOT NULL,
    username VARCHAR(50) NOT NULL,
    reservation_date TIMESTAMP NOT NULL,
    pickup_deadline TIMESTAMP,
    due_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'reserved' CHECK (status IN ('reserved', 'issued', 'returned', 'cancelled')),
    PRIMARY KEY (copy_id, username, reservation_date),
    FOREIGN KEY (copy_id) REFERENCES book_copies(copy_id) ON DELETE CASCADE,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);