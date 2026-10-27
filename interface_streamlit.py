import pandas as pd
import streamlit as st

from Atividade_Supabase_Redis import (
    criar_loja, listar_lojas, atualizar_loja, apagar_loja,
    criar_produto, listar_produtos, atualizar_produto, apagar_produto,
)

ESTOQUE_BAIXO = 5

st.set_page_config(page_title="Sistema de Estoque", page_icon="📦", layout="wide")


# ---------- FUNÇÕES DE APOIO ----------
def formatar_reais(valor):
    texto = f"R$ {valor:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def situacao(quantidade):
    if quantidade == 0:
        return "🔴 Sem estoque"
    if quantidade <= ESTOQUE_BAIXO:
        return "🟡 Estoque baixo"
    return "🟢 Disponível"


def avisar(mensagem):
    # Guarda a mensagem e recarrega a página para as listas já mostrarem a mudança
    st.session_state["aviso"] = mensagem
    st.rerun()


def nome_loja(loja):
    return f"#{loja['id']} · {loja['nome']}"


def nome_produto(produto):
    return f"#{produto['id']} · {produto['nome']}"


# ---------- MENU ----------
st.sidebar.title("📦 Sistema de Estoque")
pagina = st.sidebar.radio("Navegação", ["🏬 Lojas", "📦 Produtos em estoque"])
st.sidebar.divider()
st.sidebar.caption("Dados no Supabase · cache no Redis (60 s)")

if "aviso" in st.session_state:
    st.success(st.session_state.pop("aviso"), icon="✅")

try:
    lojas = listar_lojas()
except Exception as erro:
    st.error(f"Não foi possível conectar ao banco de dados: {erro}")
    st.stop()

lojas_por_id = {loja["id"]: loja for loja in lojas}

# ---------- LOJAS ----------
if pagina == "🏬 Lojas":
    st.title("🏬 Lojas")
    st.caption("Cadastre e gerencie as lojas que possuem estoque.")
    st.metric("Lojas cadastradas", len(lojas))

    aba_lista, aba_nova, aba_editar, aba_remover = st.tabs(
        ["📋 Lojas cadastradas", "➕ Nova loja", "✏️ Editar loja", "🗑️ Remover loja"]
    )

    with aba_lista:
        if lojas:
            tabela = pd.DataFrame(
                [{"Código": l["id"], "Loja": l["nome"], "Descrição": l.get("descricao") or ""} for l in lojas]
            )
            st.dataframe(tabela, hide_index=True, width="stretch")
        else:
            st.info("Nenhuma loja cadastrada ainda. Use a aba **Nova loja** para começar.")

    with aba_nova:
        with st.form("nova_loja", clear_on_submit=True):
            nome = st.text_input("Nome da loja")
            descricao = st.text_area("Descrição")
            if st.form_submit_button("Cadastrar loja", type="primary"):
                if not nome.strip():
                    st.error("Informe o nome da loja.")
                else:
                    try:
                        criar_loja(nome.strip(), descricao.strip())
                    except Exception as erro:
                        st.error(f"Não foi possível criar a loja: {erro}")
                    else:
                        avisar(f"Loja **{nome.strip()}** criada com sucesso!")

    with aba_editar:
        if not lojas:
            st.info("Nenhuma loja para editar.")
        else:
            loja_id = st.selectbox(
                "Selecione a loja", list(lojas_por_id),
                format_func=lambda i: nome_loja(lojas_por_id[i]), key="loja_editar",
            )
            loja = lojas_por_id[loja_id]
            with st.form(f"editar_loja_{loja_id}"):
                nome = st.text_input("Nome da loja", value=loja["nome"])
                descricao = st.text_area("Descrição", value=loja.get("descricao") or "")
                if st.form_submit_button("Salvar alterações", type="primary"):
                    if not nome.strip():
                        st.error("Informe o nome da loja.")
                    else:
                        try:
                            resultado = atualizar_loja(loja_id, nome.strip(), descricao.strip())
                        except Exception as erro:
                            st.error(f"Não foi possível atualizar a loja: {erro}")
                        else:
                            if resultado:
                                avisar(f"Loja **{nome.strip()}** atualizada com sucesso!")
                            st.error("A loja não foi atualizada. Verifique as permissões da tabela no Supabase.")

    with aba_remover:
        if not lojas:
            st.info("Nenhuma loja para remover.")
        else:
            loja_id = st.selectbox(
                "Selecione a loja", list(lojas_por_id),
                format_func=lambda i: nome_loja(lojas_por_id[i]), key="loja_remover",
            )
            st.warning("Esta ação não pode ser desfeita.", icon="⚠️")
            confirmar = st.checkbox("Confirmo que quero remover esta loja", key=f"confirmar_loja_{loja_id}")
            if st.button("Remover loja", type="primary", disabled=not confirmar):
                try:
                    resultado = apagar_loja(loja_id)
                except Exception as erro:
                    st.error(f"Não foi possível remover a loja. Verifique se ainda há produtos cadastrados nela. ({erro})")
                else:
                    if resultado:
                        avisar(f"Loja **{lojas_por_id[loja_id]['nome']}** removida.")
                    st.error("A loja não foi removida. Verifique as permissões da tabela no Supabase.")

# ---------- PRODUTOS ----------
else:
    st.title("📦 Produtos em estoque")
    st.caption("Controle a quantidade, o preço e o valor dos produtos de cada loja.")

    if not lojas:
        st.info("Cadastre uma loja primeiro na página **Lojas**.")
        st.stop()

    loja_id = st.selectbox(
        "Loja", list(lojas_por_id), format_func=lambda i: nome_loja(lojas_por_id[i]), key="loja_estoque",
    )

    try:
        produtos = listar_produtos(loja_id)
    except Exception as erro:
        st.error(f"Não foi possível carregar o estoque: {erro}")
        st.stop()

    produtos_por_id = {produto["id"]: produto for produto in produtos}

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Produtos cadastrados", len(produtos))
    col2.metric("Unidades em estoque", sum(int(p["quantidade"]) for p in produtos))
    col3.metric("Valor em estoque",formatar_reais(sum(int(p["quantidade"]) * float(p["preco"]) for p in produtos)))
    col4.metric("Com estoque baixo", sum(1 for p in produtos if int(p["quantidade"]) <= ESTOQUE_BAIXO))

    aba_lista, aba_novo, aba_editar, aba_remover = st.tabs(
        ["📋 Estoque atual", "➕ Cadastrar produto", "✏️ Atualizar produto", "🗑️ Remover produto"]
    )

    with aba_lista:
        if produtos:
            tabela = pd.DataFrame(
                [
                    {
                        "Código": p["id"],
                        "Produto": p["nome"],
                        "Quantidade": int(p["quantidade"]),
                        "Preço unitário": formatar_reais(float(p["preco"])),
                        "Valor em estoque": formatar_reais(int(p["quantidade"]) * float(p["preco"])),
                        "Situação": situacao(int(p["quantidade"])),
                    }
                    for p in produtos
                ]
            )
            st.dataframe(tabela, hide_index=True, width="stretch")
        else:
            st.info("Nenhum produto cadastrado nesta loja. Use a aba **Cadastrar produto** para começar.")

    with aba_novo:
        with st.form("novo_produto", clear_on_submit=True):
            nome = st.text_input("Nome do produto")
            col_qtd, col_preco = st.columns(2)
            quantidade = col_qtd.number_input("Quantidade em estoque", min_value=0, step=1)
            preco = col_preco.number_input("Preço unitário (R$)", min_value=0.0, step=0.01, format="%.2f")
            if st.form_submit_button("Cadastrar produto", type="primary"):
                if not nome.strip():
                    st.error("Informe o nome do produto.")
                else:
                    try:
                        criar_produto(loja_id, nome.strip(), quantidade, preco)
                    except Exception as erro:
                        st.error(f"Não foi possível cadastrar o produto: {erro}")
                    else:
                        avisar(f"Produto **{nome.strip()}** cadastrado no estoque com sucesso!")

    with aba_editar:
        if not produtos:
            st.info("Nenhum produto para atualizar.")
        else:
            produto_id = st.selectbox(
                "Selecione o produto", list(produtos_por_id),
                format_func=lambda i: nome_produto(produtos_por_id[i]), key="produto_editar",
            )
            produto = produtos_por_id[produto_id]
            with st.form(f"editar_produto_{produto_id}"):
                nome = st.text_input("Nome do produto", value=produto["nome"])
                col_qtd, col_preco = st.columns(2)
                quantidade = col_qtd.number_input(
                    "Quantidade em estoque", min_value=0, step=1, value=int(produto["quantidade"])
                )
                preco = col_preco.number_input(
                    "Preço unitário (R$)", min_value=0.0, step=0.01, format="%.2f", value=float(produto["preco"])
                )
                if st.form_submit_button("Salvar alterações", type="primary"):
                    if not nome.strip():
                        st.error("Informe o nome do produto.")
                    else:
                        try:
                            resultado = atualizar_produto(produto_id, nome.strip(), quantidade, preco)
                        except Exception as erro:
                            st.error(f"Não foi possível atualizar o produto: {erro}")
                        else:
                            if resultado:
                                avisar(f"Estoque do produto **{nome.strip()}** atualizado com sucesso!")
                            st.error("O produto não foi atualizado. Verifique as permissões da tabela no Supabase.")

    with aba_remover:
        if not produtos:
            st.info("Nenhum produto para remover.")
        else:
            produto_id = st.selectbox(
                "Selecione o produto", list(produtos_por_id),
                format_func=lambda i: nome_produto(produtos_por_id[i]), key="produto_remover",
            )
            st.warning("Esta ação não pode ser desfeita.", icon="⚠️")
            confirmar = st.checkbox("Confirmo que quero remover este produto", key=f"confirmar_produto_{produto_id}")
            if st.button("Remover produto", type="primary", disabled=not confirmar):
                try:
                    resultado = apagar_produto(produto_id)
                except Exception as erro:
                    st.error(f"Não foi possível remover o produto: {erro}")
                else:
                    if resultado:
                        avisar(f"Produto **{produtos_por_id[produto_id]['nome']}** removido do estoque.")
                    st.error("O produto não foi removido. Verifique as permissões da tabela no Supabase.")
