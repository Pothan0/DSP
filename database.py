import sqlite3

DB_FILE = "sentricore.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            diagnosis TEXT,
            ssn TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            medication TEXT,
            date TEXT,
            notes TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    ''')
    
    # Insert mock data if empty
    cursor.execute("SELECT COUNT(*) FROM patients")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO patients (name, email, diagnosis, ssn) VALUES (?, ?, ?, ?)",
            [
                ("Alice Smith", "alice@example.com", "Hypertension", "111-22-3333"),
                ("Bob Jones", "bob@example.com", "Asthma", "444-55-6666"),
                ("Charlie Brown", "charlie@example.com", "Diabetes Type 2", "777-88-9999")
            ]
        )
        # Mock prescriptions
        cursor.executemany(
            "INSERT INTO prescriptions (patient_id, medication, date, notes) VALUES (?, ?, ?, ?)",
            [
                (1, "Lisinopril 10mg", "2024-03-01", "Take once daily"),
                (1, "Amlodipine 5mg", "2024-03-02", "Take once daily"),
                (2, "Albuterol Inhaler", "2024-03-01", "As needed for wheezing"),
                (3, "Metformin 500mg", "2024-03-03", "Twice daily with meals")
            ]
        )
    
    conn.commit()
    conn.close()

def get_patient_by_name(name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, diagnosis, ssn FROM patients WHERE name LIKE ?", (f"%{name}%",))
    result = cursor.fetchall()
    conn.close()
    return result

def get_prescription_history(patient_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT medication, date, notes FROM prescriptions WHERE patient_id = ?", (patient_id,))
    result = cursor.fetchall()
    conn.close()
    return result

if __name__ == "__main__":
    init_db()
    print("Database initialized with expanded dummy data.")
