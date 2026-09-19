

import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


# ============================================================
# CONFIGURATION WIS2
# ============================================================

WME_CONFORMANCE_URI = (
    "http://wis.wmo.int/spec/wme/1/conf/monitoring-event-message-core"
)

WME_DATASCHEMA = (
    "https://schemas.wmo.int/wme/1.0.0/schemas/"
    "wis2-event-message-bundled.json"
)

VALID_SEVERITIES = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}

MAX_MESSAGE_SIZE_BYTES = 8192

DEFAULT_DB_PATH = "wis2_monitor.db"


# ============================================================
# TOPICS MQTT
# ============================================================

def build_subscription_topic(centre_id="+"):
    """
    Construit le topic d'écoute WIS2.

    Tous les centres :
        monitor/a/wis2/#

    Centre spécifique :
        monitor/a/wis2/centre-id/#
    """

    if centre_id == "+":
        return "monitor/a/wis2/#"

    if not centre_id or "/" in centre_id:
        raise ValueError("centre_id invalide")

    return f"monitor/a/wis2/{centre_id}/#"


# ============================================================
# VALIDATION WMEM
# ============================================================

def validate_wmem(message):
    """
    Validation basique d'un message WIS2 Monitoring Event.
    """

    errors = []

    required_top = [
        "id",
        "specversion",
        "type",
        "source",
        "subject",
        "time",
        "datacontenttype",
        "dataschema",
        "data",
    ]

    # Vérification des champs obligatoires
    for field in required_top:
        if field not in message:
            errors.append(
                f"champ requis manquant : {field}"
            )

    # UUID
    if "id" in message:
        try:
            uuid.UUID(str(message["id"]))
        except (ValueError, AttributeError, TypeError):
            errors.append(
                "id doit être un UUID valide"
            )

    # specversion
    if message.get("specversion") != "1.0":
        errors.append(
            'specversion doit être "1.0"'
        )

    # datacontenttype
    if message.get("datacontenttype") != "application/json":
        errors.append(
            'datacontenttype doit être "application/json"'
        )

    # data
    data = message.get("data", {})

    if not isinstance(data, dict):
        errors.append(
            "data doit être un objet JSON"
        )
        data = {}

    # conformsTo
    if WME_CONFORMANCE_URI not in data.get(
        "conformsTo", []
    ):
        errors.append(
            "data.conformsTo ne contient pas "
            "l'URI WME"
        )

    # severity
    severity = data.get("severity")

    if severity not in VALID_SEVERITIES:
        errors.append(
            f"data.severity invalide : {severity}"
        )

    # content / links
    has_content = "content" in data
    has_links = "links" in data

    if not has_content and not has_links:
        errors.append(
            "data doit fournir content et/ou links"
        )

    # content
    if has_content:

        content = data.get("content")

        if not isinstance(content, dict):
            errors.append(
                "data.content doit être un objet"
            )

        elif "title" not in content:
            errors.append(
                "data.content.title est requis"
            )

    # links
    if has_links:

        links = data.get("links", [])

        if not isinstance(links, list):
            errors.append(
                "data.links doit être une liste"
            )
        else:

            allowed_schemes = (
                "http://",
                "https://",
                "ftp://",
                "sftp://",
            )

            for link in links:

                if not isinstance(link, dict):
                    errors.append(
                        "chaque élément links doit être un objet"
                    )
                    continue

                if "href" not in link or "rel" not in link:
                    errors.append(
                        "chaque link doit avoir href et rel"
                    )

                elif not link["href"].startswith(
                    allowed_schemes
                ):
                    errors.append(
                        "href doit utiliser http(s), ftp ou sftp"
                    )

    # Taille
    size = len(
        json.dumps(
            message,
            ensure_ascii=False
        ).encode("utf-8")
    )

    if size > MAX_MESSAGE_SIZE_BYTES:
        errors.append(
            f"message trop volumineux : "
            f"{size} octets > "
            f"{MAX_MESSAGE_SIZE_BYTES}"
        )

    return errors


# ============================================================
# BASE DE DONNÉES
# ============================================================

SCHEMA_SQL = """

CREATE TABLE IF NOT EXISTS wme_events (

    row_id INTEGER PRIMARY KEY AUTOINCREMENT,

    id TEXT NOT NULL UNIQUE,

    specversion TEXT NOT NULL,

    type TEXT NOT NULL,

    source TEXT NOT NULL,

    subject TEXT NOT NULL,

    event_time TEXT NOT NULL,

    datacontenttype TEXT NOT NULL,

    dataschema TEXT NOT NULL,

    severity TEXT NOT NULL,

    content_title TEXT,

    content_description TEXT,

    content_channel TEXT,

    ref TEXT,

    time_interval_start TEXT,

    time_interval_end TEXT,

    raw_json TEXT NOT NULL,

    is_valid INTEGER NOT NULL DEFAULT 1,

    validation_errors TEXT,

    received_at TEXT NOT NULL
        DEFAULT (
            strftime(
                '%Y-%m-%dT%H:%M:%SZ',
                'now'
            )
        )
);


CREATE INDEX IF NOT EXISTS idx_wme_subject
ON wme_events(subject);


CREATE INDEX IF NOT EXISTS idx_wme_source
ON wme_events(source);


CREATE INDEX IF NOT EXISTS idx_wme_severity
ON wme_events(severity);


CREATE INDEX IF NOT EXISTS idx_wme_time
ON wme_events(event_time);


CREATE TABLE IF NOT EXISTS wme_links (

    row_id INTEGER PRIMARY KEY AUTOINCREMENT,

    event_id TEXT NOT NULL,

    href TEXT NOT NULL,

    rel TEXT NOT NULL,

    type TEXT,

    length INTEGER,

    FOREIGN KEY(event_id)
        REFERENCES wme_events(id)
        ON DELETE CASCADE
);

"""


def init_db(db_path=DEFAULT_DB_PATH):

    conn = sqlite3.connect(db_path)

    try:

        conn.executescript(SCHEMA_SQL)

        conn.commit()

        print(
            f"Base de données initialisée : {db_path}"
        )

    finally:

        conn.close()


# ============================================================
# STOCKAGE
# ============================================================

def store_event(conn, message, errors):

    data = message.get("data", {})

    content = data.get(
        "content",
        {}
    ) or {}

    time_data = data.get(
        "time",
        {}
    ) or {}

    interval = time_data.get(
        "interval",
        [None, None]
    )

    conn.execute(
        """
        INSERT OR IGNORE INTO wme_events (

            id,
            specversion,
            type,
            source,
            subject,
            event_time,
            datacontenttype,
            dataschema,
            severity,

            content_title,
            content_description,
            content_channel,

            ref,

            time_interval_start,
            time_interval_end,

            raw_json,

            is_valid,
            validation_errors

        )

        VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
        """,

        (

            message.get("id"),

            message.get("specversion"),

            message.get("type"),

            message.get("source"),

            message.get("subject"),

            message.get("time"),

            message.get("datacontenttype"),

            message.get("dataschema"),

            data.get("severity"),

            content.get("title"),

            content.get("description"),

            content.get("channel"),

            data.get("ref"),

            interval[0]
            if len(interval) > 0
            else None,

            interval[1]
            if len(interval) > 1
            else None,

            json.dumps(
                message,
                ensure_ascii=False
            ),

            0 if errors else 1,

            json.dumps(
                errors,
                ensure_ascii=False
            )
            if errors
            else None,
        )
    )

    # Liens
    for link in data.get("links", []) or []:

        conn.execute(
            """
            INSERT INTO wme_links
            (
                event_id,
                href,
                rel,
                type,
                length
            )
            VALUES (?, ?, ?, ?, ?)
            """,

            (
                message.get("id"),
                link.get("href"),
                link.get("rel"),
                link.get("type"),
                link.get("length"),
            )
        )

    conn.commit()


# ============================================================
# MQTT SUBSCRIBER
# ============================================================

class Wis2MonitorSubscriber:

    def __init__(
        self,
        host,
        port,
        db_path=DEFAULT_DB_PATH,
        centre_id="+",
        username=None,
        password=None,
        use_tls=False,
    ):

        if mqtt is None:
            raise RuntimeError(
                "paho-mqtt n'est pas installé."
            )

        self.host = host
        self.port = port
        self.db_path = db_path

        self.topic = build_subscription_topic(
            centre_id
        )

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=(
                f"wis2-subscriber-"
                f"{uuid.uuid4().hex[:8]}"
            )
        )

        if username:

            self.client.username_pw_set(
                username,
                password
            )

        if use_tls:

            self.client.tls_set()

        self.client.on_connect = (
            self._on_connect
        )

        self.client.on_message = (
            self._on_message
        )

    # --------------------------------------------------------
    # CONNEXION
    # --------------------------------------------------------

    def _on_connect(
        self,
        client,
        userdata,
        flags,
        reason_code,
        properties=None
    ):

        print(
            f"Connecté au broker "
            f"{self.host}:{self.port}"
        )

        print(
            f"Code connexion : {reason_code}"
        )

        result, mid = client.subscribe(
            self.topic,
            qos=1
        )

        if result == mqtt.MQTT_ERR_SUCCESS:

            print(
                f"Abonné au topic : "
                f"{self.topic}"
            )

        else:

            print(
                f"Erreur abonnement : "
                f"{result}"
            )

    # --------------------------------------------------------
    # RÉCEPTION MESSAGE
    # --------------------------------------------------------

    def _on_message(
        self,
        client,
        userdata,
        msg
    ):

        received_at = datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        print()
        print("=" * 70)
        print(
            f"Message reçu : {received_at}"
        )
        print(
            f"Topic : {msg.topic}"
        )

        # Décodage JSON
        try:

            payload = msg.payload.decode(
                "utf-8"
            )

            message = json.loads(payload)

        except UnicodeDecodeError:

            print(
                "ERREUR : payload UTF-8 invalide"
            )

            return

        except json.JSONDecodeError:

            print(
                "ERREUR : payload non JSON"
            )

            return

        # Validation
        errors = validate_wmem(
            message
        )

        if errors:

            status = "INVALIDE"

        else:

            status = "VALIDE"

        data = message.get(
            "data",
            {}
        )

        severity = data.get(
            "severity",
            "UNKNOWN"
        )

        content = data.get(
            "content",
            {}
        ) or {}

        title = content.get(
            "title",
            "(sans titre)"
        )

        source = message.get(
            "source",
            "UNKNOWN"
        )

        subject = message.get(
            "subject",
            "UNKNOWN"
        )

        print(
            f"Status   : {status}"
        )

        print(
            f"Severity : {severity}"
        )

        print(
            f"Source   : {source}"
        )

        print(
            f"Subject  : {subject}"
        )

        print(
            f"Title    : {title}"
        )

        if errors:

            print()
            print("Erreurs :")

            for error in errors:

                print(
                    f"  - {error}"
                )

        # Stockage
        conn = sqlite3.connect(
            self.db_path
        )

        try:

            store_event(
                conn,
                message,
                errors
            )

        except Exception as e:

            print(
                f"ERREUR SQLite : {e}"
            )

        finally:

            conn.close()

        print("=" * 70)

    # --------------------------------------------------------
    # BOUCLE PRINCIPALE
    # --------------------------------------------------------

    def run_forever(self):

        init_db(
            self.db_path
        )

        print()
        print(
            "Connexion au broker MQTT..."
        )

        self.client.connect(
            self.host,
            self.port,
            keepalive=60
        )

        print()
        print(
            "Écoute des événements "
            "de monitoring WIS2..."
        )

        print(
            "Appuyez sur Ctrl+C pour arrêter."
        )

        try:

            self.client.loop_forever()

        except KeyboardInterrupt:

            print()
            print(
                "Arrêt demandé."
            )

        finally:

            self.client.disconnect()


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "WIS2 Monitoring - "
            "Écoute MQTT + validation + SQLite"
        )
    )

    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help="chemin de la base SQLite"
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True
    )

    # --------------------------------------------------------
    # INIT DB
    # --------------------------------------------------------

    sub.add_parser(
        "initdb",
        help="initialiser la base SQLite"
    )

    # --------------------------------------------------------
    # LISTEN
    # --------------------------------------------------------

    p_listen = sub.add_parser(
        "listen",
        help=(
            "écouter les événements "
            "de monitoring WIS2"
        )
    )

    p_listen.add_argument(
        "--host",
        required=True,
        help="adresse du broker MQTT"
    )

    p_listen.add_argument(
        "--port",
        type=int,
        default=1883,
        help="port MQTT"
    )

    p_listen.add_argument(
        "--centre-id",
        default="+",
        help=(
            "centre spécifique "
            "(défaut : tous les centres)"
        )
    )

    p_listen.add_argument(
        "--username"
    )

    p_listen.add_argument(
        "--password"
    )

    p_listen.add_argument(
        "--tls",
        action="store_true"
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # INIT
    # --------------------------------------------------------

    if args.command == "initdb":

        init_db(
            args.db
        )

    # --------------------------------------------------------
    # LISTEN
    # --------------------------------------------------------

    elif args.command == "listen":

        subscriber = Wis2MonitorSubscriber(

            host=args.host,

            port=args.port,

            db_path=args.db,

            centre_id=args.centre_id,

            username=args.username,

            password=args.password,

            use_tls=args.tls,
        )

        subscriber.run_forever()


if __name__ == "__main__":

    sys.exit(main())