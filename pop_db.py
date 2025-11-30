"""
Codigo para popularizacao do banco

Seed com:
- 100 users
- cada user com 3-5 residences
- cada residence com 10-20 scans
- objetos detectados por scan (repetidos e novos)
- histórico de mudanças (moved, renamed, color change, removed) coerente
"""

import random
import hashlib
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, BulkWriteError
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

# CONFIGURAÇÃO: substitua pela sua URI se quiser
MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB")

# Parâmetros de geração
NUM_USERS = 100
MIN_RES_PER_USER = 3
MAX_RES_PER_USER = 5
MIN_SCANS_PER_RES = 10
MAX_SCANS_PER_RES = 20
MAX_OBJECTS_PER_SCAN = 8    # 0..8 objetos por scan
MAX_HISTORY_ENTRIES_PER_OBJECT = 4

# Listas de apoio (nomes, tipos, cores, etc.)
first_names = ["João", "Lucas", "Mariana", "Ana", "Carlos", "Fernanda", "Pedro", "Rafaela", "Gustavo", "Beatriz",
               "Marcos", "Patrícia", "Paulo", "Laura", "Ricardo", "Juliana", "Roberto", "Carolina", "Thiago", "Sofia"]
last_names = ["Silva", "Souza", "Oliveira", "Santos", "Pereira", "Costa", "Almeida", "Gomes", "Ribeiro", "Martins"]
room_names = ["Sala", "Cozinha", "Quarto 1", "Quarto 2", "Banheiro", "Escritório", "Varanda"]
object_types = ["móvel", "eletrônico", "decoração", "utensílio", "eletrodoméstico"]
object_base_names = ["Sofá", "Mesa", "Cadeira", "Cama", "Armário", "TV", "Geladeira", "Micro-ondas", "Prateleira", "Tapete"]
colors = ["azul", "vermelho", "verde", "preto", "branco", "cinza", "marrom", "amarelo", "bege"]

def make_vision_hash(name, coords, seed=None):
    s = f"{name}-{coords}-{seed or uuid.uuid4().hex}"
    return hashlib.sha1(s.encode()).hexdigest()[:16]

def jitter_coords(base_x=0.0, base_y=0.0, base_z=0.0):
    return {
        "x": round(base_x + random.uniform(-0.8, 0.8), 3),
        "y": round(base_y + random.uniform(-0.8, 0.8), 3),
        "z": round(base_z + random.uniform(-0.1, 0.6), 3)
    }

def random_timestamp(start_date, scan_index):
    # Gera timestamps próximos entre si para evitar colisões de unique index por residence+timestamp
    # start_date é datetime; adiciona alguns minutos/horas/dias
    delta = timedelta(days=random.randint(0, 90), hours=random.randint(0, 23), minutes=random.randint(0, 59))
    # também adiciona um pouco baseado no índice do scan para evitar colisões
    delta += timedelta(minutes=scan_index * random.randint(1, 10))
    return start_date + delta

def main():
    client = MongoClient(MONGO_URI, server_api=ServerApi('1'))

    print("Conectando ao MongoDB ...")
    try:
        client.admin.command("ping")
    except Exception as e:
        raise SystemExit(f"Erro ao conectar ao MongoDB: {e}")
    
    db = client[DB_NAME]

    users_col = db.users
    residences_col = db.residences
    scans_col = db.scans
    objects_col = db.objects
    history_col = db.history

    # Contadores para imprimir ao final
    total_users = 0
    total_residences = 0
    total_scans = 0
    total_objects = 0
    total_history = 0

    base_start_date = datetime.utcnow() - timedelta(days=120)

    for u_idx in range(NUM_USERS):
        # Criar usuário
        first = random.choice(first_names)
        last = random.choice(last_names)
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{u_idx}@example.com"
        user_doc = {
            "name": name,
            "email": email,
            "password_hash": hashlib.sha256((email + "password").encode()).hexdigest(),
            "created_at": base_start_date + timedelta(days=random.randint(0, 100)),
            "preferences": {
                "voice": random.choice(["masculino", "feminino"]),
                "language": "pt"
            }
        }

        try:
            user_res = users_col.insert_one(user_doc)
        except DuplicateKeyError:
            # caso raro de e-mail duplicado (devido a nomes iguais), adicione sufixo
            user_doc["email"] = f"{first.lower()}.{last.lower()}.{u_idx}.{uuid.uuid4().hex[:6]}@example.com"
            user_res = users_col.insert_one(user_doc)

        user_id = user_res.inserted_id
        total_users += 1

        # Escolher quantas residências esse usuário tem
        num_res = random.randint(MIN_RES_PER_USER, MAX_RES_PER_USER)

        for r in range(num_res):
            res_name = random.choice(room_names) + (f" - {r+1}" if r > 0 else "")
            residence_doc = {
                "user_id": user_id,
                "name": res_name,
                "address": f"Rua {random.choice(['A', 'B', 'C', 'D', 'E'])}, {random.randint(1,999)}",
                "description": f"{random.choice(['Apartamento','Casa','Sobrado'])} {random.randint(1,4)} quartos",
                "created_at": base_start_date + timedelta(days=random.randint(0, 100)),
                "metadata": {
                    "area_m2": random.randint(30, 250)
                }
            }
            res_res = residences_col.insert_one(residence_doc)
            residence_id = res_res.inserted_id
            total_residences += 1

            # Para manter alguns "objetos comuns" por residência para termos repetições entre scans
            # Criar um pequeno "catálogo" de objetos persistentes para a residência
            num_persistent_objects = random.randint(3, 7)
            persistent_objects = []
            for p in range(num_persistent_objects):
                base_name = random.choice(object_base_names)
                obj_name = f"{base_name} #{p+1}"
                coords = jitter_coords(base_x=random.uniform(0,4), base_y=random.uniform(0,4), base_z=0)
                vision_hash = make_vision_hash(obj_name, coords, seed=str(uuid.uuid4()))
                obj_doc = {
                    "residence_id": residence_id,
                    "name": obj_name,
                    "type": random.choice(object_types),
                    "color": random.choice(colors),
                    "coordinates": coords,
                    # nota: scan_id e timestamps serão setados quando detectados
                    "scan_id": None,
                    "first_seen": None,
                    "last_seen": None,
                    "status": "ativo",
                    "confidence": round(random.uniform(0.7, 0.99), 3),
                    "vision_hash": vision_hash
                }
                persistent_objects.append(obj_doc)

            # Scans
            num_scans = random.randint(MIN_SCANS_PER_RES, MAX_SCANS_PER_RES)
            scan_start_date = base_start_date + timedelta(days=random.randint(0, 60))
            # rastrear objetos inseridos por residência para poder criar histórico
            inserted_objects_by_hash = {}  # vision_hash -> object_id

            for s_idx in range(num_scans):
                scan_time = random_timestamp(scan_start_date, s_idx)
                scan_doc = {
                    "residence_id": residence_id,
                    "user_id": user_id,
                    "timestamp": scan_time,
                    "camera_meta": {
                        "device": random.choice(["iPhone 12", "iPhone 13", "Pixel 6", "Galaxy S21"]),
                        "fov": random.choice([90, 100, 110, 120]),
                        "position": {"x": round(random.uniform(0,4),3), "y": round(random.uniform(0,4),3), "z": round(random.uniform(0.5,2.0),3)}
                    },
                    "objects_detected_count": 0  # atualizaremos após detectar
                }

                # Inserir scan (cuidando de unique index residence+timestamp)
                try:
                    scan_res = scans_col.insert_one(scan_doc)
                except DuplicateKeyError:
                    # se timestamp colidir, desloca por alguns segundos e tenta de novo
                    scan_doc["timestamp"] = scan_time + timedelta(seconds=random.randint(1,300))
                    scan_res = scans_col.insert_one(scan_doc)

                scan_id = scan_res.inserted_id
                total_scans += 1

                # quantos objetos este scan detecta? pode ser 0 (cenário pedido)
                n_objs = random.randint(0, MAX_OBJECTS_PER_SCAN)
                scan_objects = []

                # misturar objetos persistentes e novos
                # escolher quantos dos persistentes incluir
                if persistent_objects and n_objs > 0:
                    from_persistent = random.randint(0, min(len(persistent_objects), n_objs))
                else:
                    from_persistent = 0
                from_transient = n_objs - from_persistent

                # inserir objetos persistentes
                chosen_persistent = random.sample(persistent_objects, from_persistent) if from_persistent else []
                for p_obj in chosen_persistent:
                    # Leve jitter nas coordenadas para simular movimento de detecção
                    coords = jitter_coords(
                        base_x=p_obj["coordinates"]["x"],
                        base_y=p_obj["coordinates"]["y"],
                        base_z=p_obj["coordinates"]["z"]
                    )
                    vision_hash = p_obj["vision_hash"]
                    # preparar doc do objeto para inserção (irá setar scan_id e timestamps)
                    obj_doc = {
                        "residence_id": residence_id,
                        "name": p_obj["name"],
                        "type": p_obj["type"],
                        "color": p_obj["color"],
                        "coordinates": coords,
                        "scan_id": scan_id,
                        "first_seen": scan_time,
                        "last_seen": scan_time,
                        "status": "ativo",
                        "confidence": round(random.uniform(0.6, 0.99), 3),
                        "vision_hash": vision_hash
                    }
                    scan_objects.append(obj_doc)

                # inserir objetos transitórios/novos
                for t in range(from_transient):
                    base_name = random.choice(object_base_names)
                    obj_name = f"{base_name} (scan{str(s_idx+1)})"
                    coords = jitter_coords(base_x=random.uniform(0,4), base_y=random.uniform(0,4), base_z=random.uniform(0,1))
                    vision_hash = make_vision_hash(obj_name, coords)
                    obj_doc = {
                        "residence_id": residence_id,
                        "name": obj_name,
                        "type": random.choice(object_types),
                        "color": random.choice(colors),
                        "coordinates": coords,
                        "scan_id": scan_id,
                        "first_seen": scan_time,
                        "last_seen": scan_time,
                        "status": "ativo",
                        "confidence": round(random.uniform(0.5, 0.98), 3),
                        "vision_hash": vision_hash
                    }
                    scan_objects.append(obj_doc)

                # inserir objetos detectados neste scan (tratando possíveis duplicatas/unique index vision_hash+residence_id)
                inserted_ids_this_scan = []
                for obj in scan_objects:
                    try:
                        res = objects_col.insert_one(obj)
                        obj_id = res.inserted_id
                        total_objects += 1
                        inserted_ids_this_scan.append((obj_id, obj))
                        # rastrear por vision_hash
                        inserted_objects_by_hash[obj["vision_hash"]] = {
                            "object_id": obj_id,
                            "last_seen": obj["last_seen"],
                            "name": obj["name"],
                            "color": obj["color"],
                            "coordinates": obj["coordinates"]
                        }
                    except DuplicateKeyError:
                        # Já existe um objeto com mesmo vision_hash e residence_id.
                        # Podemos atualizar o last_seen/scan_id para manter histórico coerente.
                        existing = objects_col.find_one({"vision_hash": obj["vision_hash"], "residence_id": residence_id})
                        if existing:
                            update_doc = {
                                "$set": {
                                    "last_seen": obj["last_seen"],
                                    "scan_id": scan_id,
                                    "coordinates": obj["coordinates"],
                                    "confidence": obj["confidence"]
                                }
                            }
                            objects_col.update_one({"_id": existing["_id"]}, update_doc)
                            inserted_ids_this_scan.append((existing["_id"], obj))
                            inserted_objects_by_hash[obj["vision_hash"]] = {
                                "object_id": existing["_id"],
                                "last_seen": obj["last_seen"],
                                "name": obj["name"],
                                "color": obj["color"],
                                "coordinates": obj["coordinates"]
                            }
                        else:
                            # Caso raro onde procura por doc similar por visão falha -> ignora para evitar crash
                            continue

                # Atualiza campo objects_detected_count no scan
                scans_col.update_one({"_id": scan_id}, {"$set": {"objects_detected_count": len(inserted_ids_this_scan)}})

                # Gerar histórico aleatório para alguns objetos (moved, renamed, color change, removed)
                for (obj_id, obj) in inserted_ids_this_scan:
                    # criar 0..MAX_HISTORY_ENTRIES_PER_OBJECT entradas ao longo do tempo
                    num_hist = random.randint(0, MAX_HISTORY_ENTRIES_PER_OBJECT)
                    for h in range(num_hist):
                        action_time = obj["last_seen"] + timedelta(minutes=random.randint(1, 60*(h+1)))
                        action_type = random.choices(
                            ["moved", "renamed", "color_changed", "removed", "status_update"],
                            weights=[0.4, 0.15, 0.15, 0.05, 0.25],
                            k=1
                        )[0]
                        history_doc = {
                            "object_id": obj_id,
                            "action_type": action_time and action_type or "moved",  # ensure non-empty
                            "performed_by": user_id,
                            "timestamp": action_time,
                            "notes": "",
                            "old_coordinates": None,
                            "new_coordinates": None,
                            "old_color": None,
                            "new_color": None,
                            "old_name": None,
                            "new_name": None
                        }

                        if action_type == "moved":
                            old_coords = obj["coordinates"]
                            new_coords = jitter_coords(base_x=old_coords["x"], base_y=old_coords["y"], base_z=old_coords["z"])
                            history_doc["old_coordinates"] = old_coords
                            history_doc["new_coordinates"] = new_coords
                            history_doc["notes"] = f"Objeto movido dentro da residência {res_name}."
                            # também atualiza objeto no banco
                            objects_col.update_one({"_id": obj_id}, {"$set": {"coordinates": new_coords, "last_seen": action_time}})
                        elif action_type == "renamed":
                            old_name = obj["name"]
                            new_name = old_name + " (renomeado)"
                            history_doc["old_name"] = old_name
                            history_doc["new_name"] = new_name
                            history_doc["notes"] = "Nome alterado pelo usuário."
                            objects_col.update_one({"_id": obj_id}, {"$set": {"name": new_name, "last_seen": action_time}})
                        elif action_type == "color_changed":
                            old_color = obj["color"]
                            new_color = random.choice([c for c in colors if c != old_color])
                            history_doc["old_color"] = old_color
                            history_doc["new_color"] = new_color
                            history_doc["notes"] = "Cor atualizada após nova detecção."
                            objects_col.update_one({"_id": obj_id}, {"$set": {"color": new_color, "last_seen": action_time}})
                        elif action_type == "removed":
                            history_doc["notes"] = "Objeto removido."
                            objects_col.update_one({"_id": obj_id}, {"$set": {"status": "removido", "last_seen": action_time}})
                        else:
                            # status_update or other small event
                            history_doc["notes"] = "Atualização de status automática."
                            objects_col.update_one({"_id": obj_id}, {"$set": {"last_seen": action_time}})

                        # Inserir histórico
                        try:
                            history_col.insert_one(history_doc)
                            total_history += 1
                        except DuplicateKeyError:
                            # raríssimo: continuar
                            continue

            # Após todos os scans, garantir que os objetos persistentes sejam inseridos se nunca apareceram
            for p_obj in persistent_objects:
                if p_obj["vision_hash"] not in inserted_objects_by_hash:
                    # inserir com timestamps da criação da residência
                    p_obj_doc = p_obj.copy()
                    p_obj_doc.update({
                        "scan_id": None,
                        "first_seen": residence_doc["created_at"],
                        "last_seen": residence_doc["created_at"],
                    })
                    try:
                        res = objects_col.insert_one(p_obj_doc)
                        total_objects += 1
                        inserted_objects_by_hash[p_obj["vision_hash"]] = {
                            "object_id": res.inserted_id,
                            "last_seen": p_obj_doc["last_seen"]
                        }
                    except DuplicateKeyError:
                        # se já existir ok
                        continue

    print("==== População finalizada ====")
    print(f"Usuários criados: {total_users}")
    print(f"Residências criadas: {total_residences}")
    print(f"Scans criados: {total_scans}")
    print(f"Objetos criados/atualizados: {total_objects}")
    print(f"Entradas de histórico criadas: {total_history}")
    print("Concluído.")

if __name__ == "__main__":
    main()
