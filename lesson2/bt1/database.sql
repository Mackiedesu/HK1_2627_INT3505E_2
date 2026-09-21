BEGIN TRANSACTION;
CREATE TABLE books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                isbn TEXT,
                price REAL DEFAULT 0.0
            );
INSERT INTO "books" VALUES(1,'Clean Code','Robert Martin','978-0132350884',29.99);
INSERT INTO "books" VALUES(2,'Clean Architecture','Robert Martin','978-0134494166',34.99);
INSERT INTO "books" VALUES(3,'1984','George Orwell','978-0451524935',12.99);
INSERT INTO "books" VALUES(4,'Animal Farm','George Orwell','978-0451526342',9.99);
CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL DEFAULT 'pending',
                items TEXT,
                total_price REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
INSERT INTO "orders" VALUES(1,'pending','Clean Code (1x)',29.99,'2026-09-21 18:04:35');
INSERT INTO "orders" VALUES(2,'shipped','Clean Architecture (1x)',34.99,'2026-09-21 18:04:35');
INSERT INTO "orders" VALUES(3,'delivered','1984 (2x)',25.98,'2026-09-21 18:04:35');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('orders',3);
INSERT INTO "sqlite_sequence" VALUES('books',4);
COMMIT;
