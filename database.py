import sqlite3

DB_FILE = "sentricore.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            balance REAL,
            ssn TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            amount REAL,
            date TEXT,
            description TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    ''')
    
    # Insert mock data if empty
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO customers (name, email, balance, ssn) VALUES (?, ?, ?, ?)",
            [
                ("Alice Smith", "alice@example.com", 1500.50, "111-22-3333"),
                ("Bob Jones", "bob@example.com", 25.00, "444-55-6666"),
                ("Charlie Brown", "charlie@example.com", 9999.99, "777-88-9999")
            ]
        )
        # Mock transactions
        cursor.executemany(
            "INSERT INTO transactions (customer_id, amount, date, description) VALUES (?, ?, ?, ?)",
            [
                (1, -50.00, "2024-03-01", "Grocery Store"),
                (1, -20.00, "2024-03-02", "Coffee Shop"),
                (2, 1000.00, "2024-03-01", "Salary Deposit"),
                (3, -500.00, "2024-03-03", "Rent Payment")
            ]
        )
    
    conn.commit()
    conn.close()

def get_customer_by_name(name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, balance, ssn FROM customers WHERE name LIKE ?", (f"%{name}%",))
    result = cursor.fetchall()
    conn.close()
    return result

def get_transaction_history(customer_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT amount, date, description FROM transactions WHERE customer_id = ?", (customer_id,))
    result = cursor.fetchall()
    conn.close()
    return result

if __name__ == "__main__":
    init_db()
    print("Database initialized with expanded dummy data.")

