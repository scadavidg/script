import requests
import base64
import time
import psycopg2
import uuid
import os

# ⚙️ Leer variables de entorno
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")
MAX_ARTISTS = int(os.getenv("MAX_ARTISTS", "10"))  # Valor por defecto: 100

# 🔐 Obtener token de Spotify
def get_token():
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64_auth}"
    }
    data = {
        "grant_type": "client_credentials"
    }
    response = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

# 🔍 Obtener artistas y álbumes
def obtener_bandas_y_albums(token, genero="rock", max_artistas=1000):
    headers = {
        "Authorization": f"Bearer {token}"
    }
    datos = set()

    for offset in range(0, max_artistas, 50):
        print(f"🎸 Buscando artistas rock offset={offset}")
        params = {
            "q": f"genre:{genero}",
            "type": "artist",
            "limit": 50,
            "offset": offset
        }
        r = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)
        if r.status_code != 200:
            print("❌ Error:", r.status_code, r.text)
            break

        artistas = r.json().get("artists", {}).get("items", [])
        for artista in artistas:
            artist_id = artista["id"]
            nombre_banda = artista["name"]
            datos.add(nombre_banda)

            alb_r = requests.get(f"https://api.spotify.com/v1/artists/{artist_id}/albums",
                                 headers=headers,
                                 params={"include_groups": "album", "limit": 10})
            albums = alb_r.json().get("items", [])
            for album in albums:
                datos.add(album["name"])
        time.sleep(0.2)

    return sorted(list(datos))

# 💾 Insertar palabras clave en la BD
def insertar_keywords_en_db(palabras_clave):
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()

        for keyword in palabras_clave:
            cur.execute("SELECT 1 FROM RockKeyword WHERE keyword = %s LIMIT 1;", (keyword,))
            if cur.fetchone() is None:
                cur.execute("INSERT INTO keywords (id, keyword) VALUES (%s, %s);", (str(uuid.uuid4()), keyword))

        conn.commit()
        print(f"✅ Se insertaron {len(palabras_clave)} palabras clave (únicas).")
    except Exception as e:
        import traceback
        print("❌ Error al insertar en la base de datos:", e)
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Script iniciado")
    token = get_token()
    print("🔑 Token obtenido")
    palabras_clave = obtener_bandas_y_albums(token, genero="rock", max_artistas=MAX_ARTISTS)
    print(f"🧪 {len(palabras_clave)} palabras clave encontradas")
    insertar_keywords_en_db(palabras_clave)