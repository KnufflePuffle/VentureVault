import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load credentials from .env file
load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

# Prüfen, ob alle erforderlichen Werte vorhanden sind
if not all([DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME]):
    print("FEHLER: Einige Datenbankeinstellungen fehlen in der .env-Datei")
    # Beenden des Programms oder andere Fehlerbehandlung


def get_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return connection
    except Error as e:
        print(f"Fehler beim Verbinden mit MySQL Datenbank: {e}")
        return None


def init_db():
    """Initialize the database and create necessary tables if they don't exist"""
    connection = get_connection()
    if not connection:
        print("Fehler bei der Verbindung zur Datenbank. Check die Anmeldeinformationen.")
        return False

    cursor = connection.cursor()

    # Create plotpoints table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS plotpoints (
        id VARCHAR(10) PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        status VARCHAR(20) DEFAULT 'Inactive',
        channel_id VARCHAR(20) DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    connection.commit()
    cursor.close()
    connection.close()
    print("Database initialized successfully")
    return True


def get_plotpoints():
    """Get all plotpoints from the database, ordered by ID"""
    connection = get_connection()
    if not connection:
        return []

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM plotpoints ORDER BY id")
    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    return rows


def get_plotpoint_by_id(plotpoint_id):
    """Get a specific plotpoint by ID"""
    connection = get_connection()
    if not connection:
        return None

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM plotpoints WHERE id = %s", (plotpoint_id,))
    row = cursor.fetchone()

    cursor.close()
    connection.close()

    return row


def add_plot_point(plotpoint_id, title, description):
    """Add a new plotpoint to the database"""
    connection = get_connection()
    if not connection:
        return False

    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO plotpoints (id, title, description) VALUES (%s, %s, %s)",
            (plotpoint_id, title, description)
        )
        connection.commit()
        success = True
    except Error as e:
        print(f"Fehler beim Hinzufügen des plotpoint: {e}")
        connection.rollback()
        success = False

    cursor.close()
    connection.close()

    return success


def update_plotpoint_status(plotpoint_id, status, channel_id=None):
    """Update a plotpoint's status and channel ID"""
    connection = get_connection()
    if not connection:
        return False

    cursor = connection.cursor()
    try:
        if channel_id:
            cursor.execute(
                "UPDATE plotpoints SET status = %s, channel_id = %s WHERE id = %s",
                (status, channel_id, plotpoint_id)
            )
        else:
            cursor.execute(
                "UPDATE plotpoints SET status = %s, channel_id = NULL WHERE id = %s",
                (status, plotpoint_id)
            )
        connection.commit()
        success = True
    except Error as e:
        print(f"Fehler beim updaten von plotpoint: {e}")
        connection.rollback()
        success = False

    cursor.close()
    connection.close()

    return success


def delete_plotpoint(plotpoint_id):
    """Delete a plotpoint from the database"""
    connection = get_connection()
    if not connection:
        return False

    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM plotpoints WHERE id = %s", (plotpoint_id,))
        connection.commit()
        success = True
    except Error as e:
        print(f"Fehler beim Löschen von plotpoint: {e}")
        connection.rollback()
        success = False

    cursor.close()
    connection.close()

    return success


def plotpoint_exists(plotpoint_id):
    """Check if a plotpoint with the given ID exists"""
    connection = get_connection()
    if not connection:
        return False

    cursor = connection.cursor()
    cursor.execute("SELECT id FROM plotpoints WHERE id = %s", (plotpoint_id,))
    exists = cursor.fetchone() is not None

    cursor.close()
    connection.close()

    return exists