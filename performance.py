import sqlite3
import json
import time
import os
import tempfile

# On importe la fonction de validation
# depuis ton programme principal
from wis2_monitor import validate_wmem


DB_PATH = "wis2_monitor.db"


# ============================================================
# LECTURE DES ÉVÉNEMENTS EXISTANTS
# ============================================================

def load_events():
    conn = sqlite3.connect(DB_PATH)

    cursor = conn.execute("""
        SELECT
            id,
            raw_json,
            is_valid
        FROM wme_events
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


# ============================================================
# TEST DE VALIDATION
# ============================================================

def test_validation(events):

    print("\n" + "=" * 60)
    print("TEST DE PERFORMANCE - VALIDATION")
    print("=" * 60)

    total = len(events)

    valid = 0
    invalid = 0

    start_time = time.perf_counter()

    for event_id, raw_json, stored_is_valid in events:

        try:
            message = json.loads(raw_json)

            errors = validate_wmem(message)

            if errors:
                invalid += 1
            else:
                valid += 1

        except Exception:
            invalid += 1

    end_time = time.perf_counter()

    total_time = end_time - start_time

    if total > 0:
        avg_time = total_time / total
        events_per_second = total / total_time
        validation_rate = (valid / total) * 100
    else:
        avg_time = 0
        events_per_second = 0
        validation_rate = 0

    print(f"\n📥 Événements analysés : {total}")

    print("\n🔍 Résultat de validation")
    print(f"   ✅ Valides   : {valid}")
    print(f"   ❌ Invalides : {invalid}")
    print(f"   📊 Taux de validation : {validation_rate:.2f}%")

    print("\n⏱️ Performance")
    print(f"   Temps total : {total_time:.4f} secondes")
    print(f"   Temps moyen par message : {avg_time * 1000:.4f} ms")
    print(f"   Débit : {events_per_second:.2f} événements/seconde")

    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "validation_rate": validation_rate,
        "total_time": total_time,
        "avg_time": avg_time,
        "events_per_second": events_per_second
    }


# ============================================================
# TEST DE STOCKAGE SQLITE
# ============================================================

def test_storage(events):

    print("\n" + "=" * 60)
    print("TEST DE PERFORMANCE - STOCKAGE SQLITE")
    print("=" * 60)

    # Base temporaire
    temp_db = tempfile.NamedTemporaryFile(
        suffix=".db",
        delete=False
    )

    temp_db.close()

    temp_path = temp_db.name

    conn = sqlite3.connect(temp_path)

    # Table simplifiée pour le benchmark
    conn.execute("""
        CREATE TABLE wme_events (
            id TEXT PRIMARY KEY,
            raw_json TEXT NOT NULL,
            is_valid INTEGER NOT NULL
        )
    """)

    conn.commit()

    total = len(events)

    start_time = time.perf_counter()

    for event_id, raw_json, stored_is_valid in events:

        conn.execute("""
            INSERT INTO wme_events
            (
                id,
                raw_json,
                is_valid
            )
            VALUES (?, ?, ?)
        """, (
            event_id,
            raw_json,
            stored_is_valid
        ))

    conn.commit()

    end_time = time.perf_counter()

    total_time = end_time - start_time

    conn.close()

    # Suppression de la base temporaire
    os.remove(temp_path)

    if total > 0:
        avg_time = total_time / total
        events_per_second = total / total_time
    else:
        avg_time = 0
        events_per_second = 0

    print(f"\n💾 Événements stockés : {total}")

    print("\n⏱️ Performance")
    print(f"   Temps total : {total_time:.4f} secondes")
    print(f"   Temps moyen par événement : {avg_time * 1000:.4f} ms")
    print(f"   Débit : {events_per_second:.2f} événements/seconde")

    return {
        "total": total,
        "total_time": total_time,
        "avg_time": avg_time,
        "events_per_second": events_per_second
    }


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():

    print("\n")
    print("=" * 60)
    print("       PERFORMANCE DU SYSTÈME WIS2")
    print("=" * 60)

    print("\n📂 Base utilisée :", DB_PATH)

    # Vérification
    if not os.path.exists(DB_PATH):
        print("\n❌ Base de données introuvable.")
        return

    # Chargement
    events = load_events()

    if not events:
        print("\n❌ Aucun événement trouvé.")
        return

    print(f"📥 {len(events)} événements trouvés dans la base.")

    # Test validation
    validation = test_validation(events)

    # Test stockage
    storage = test_storage(events)

    # ========================================================
    # RÉSUMÉ FINAL
    # ========================================================

    print("\n" + "=" * 60)
    print("              RÉSUMÉ FINAL")
    print("=" * 60)

    print(f"""
📊 DONNÉES
   Événements analysés : {validation['total']}
   Événements valides  : {validation['valid']}
   Événements invalides: {validation['invalid']}
   Taux de validation  : {validation['validation_rate']:.2f}%

🔍 VALIDATION
   Temps total : {validation['total_time']:.4f} s
   Temps moyen : {validation['avg_time'] * 1000:.4f} ms/message
   Débit       : {validation['events_per_second']:.2f} événements/s

💾 STOCKAGE SQLITE
   Temps total : {storage['total_time']:.4f} s
   Temps moyen : {storage['avg_time'] * 1000:.4f} ms/événement
   Débit       : {storage['events_per_second']:.2f} événements/s
""")

    print("=" * 60)
    print("✅ Test terminé.")
    print("ℹ️ La base wis2_monitor.db originale n'a pas été modifiée.")
    print("=" * 60)


if __name__ == "__main__":
    main()