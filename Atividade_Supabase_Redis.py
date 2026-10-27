import json
from supabase import create_client

S_URL="URLSupabase"
S_KEY="senha_Supabase"

supabase = create_client(S_URL, S_KEY)

import redis

r = redis.Redis(
    host='Host',
    port=19247,
    decode_responses=True,
    username="default",
    password="senha_Redis",
)

def criar_loja(nome, descricao):
    resultado = supabase.table("lojas").insert({"nome": nome, "descricao": descricao}).execute().data
    r.delete("lojas")
    return resultado

def listar_lojas():
    em_cache = r.get("lojas")
    if em_cache:
        return json.loads(em_cache)

    lojas = supabase.table("lojas").select("*").execute().data
    r.set("lojas", json.dumps(lojas), ex=60)
    return lojas

def atualizar_loja(id, nome, descricao):
    resultado = supabase.table("lojas").update({"nome": nome, "descricao": descricao}).eq("id", id).execute().data
    r.delete("lojas")
    return resultado

def apagar_loja(id):
    resultado = supabase.table("lojas").delete().eq("id", id).execute().data
    r.delete("lojas", f"produtos:{id}")
    return resultado

# ---------- PRODUTOS ----------
def criar_produto(loja_id, nome, quantidade, preco):
    resultado = supabase.table("produtos").insert({"loja_id": loja_id, "nome": nome, "quantidade": quantidade, "preco": preco}).execute().data
    r.delete(f"produtos:{loja_id}")
    return resultado

def listar_produtos(loja_id):
    em_cache = r.get(f"produtos:{loja_id}")
    if em_cache:
        return json.loads(em_cache)

    produtos = supabase.table("produtos").select("*").eq("loja_id", loja_id).execute().data
    r.set(f"produtos:{loja_id}", json.dumps(produtos), ex=60)
    return produtos

def atualizar_produto(id, nome, quantidade, preco):
    resultado = supabase.table("produtos").update({"nome": nome, "quantidade": quantidade, "preco": preco}).eq("id", id).execute().data
    if resultado:
        r.delete(f"produtos:{resultado[0]['loja_id']}")
    return resultado

def apagar_produto(id):
    resultado = supabase.table("produtos").delete().eq("id", id).execute().data
    if resultado:
        r.delete(f"produtos:{resultado[0]['loja_id']}")
    return resultado