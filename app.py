import streamlit as st
import os
from dotenv import load_dotenv
from db import get_connection
from r2 import upload_imagem

load_dotenv()

st.set_page_config(page_title="Linhas de Ônibus", layout="wide")
st.markdown("""
<style>
img {
    max-width: 300px !important;
    margin: auto;
    display: block;
}
</style>
""", unsafe_allow_html=True)
st.title("🚍 Linhas de Ônibus – Finais de Linha")

# =========================
# LOGIN SIMPLES
# =========================
def login():
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.sidebar.subheader("🔐 Acesso restrito")
        user = st.sidebar.text_input("Usuário")
        password = st.sidebar.text_input("Senha", type="password")

        if st.sidebar.button("Entrar"):
            if (
                user == os.getenv("ADMIN_USER")
                and password == os.getenv("ADMIN_PASSWORD")
            ):
                st.session_state.logado = True
                st.rerun()
            else:
                st.sidebar.error("Usuário ou senha inválidos")

login()

conn = get_connection()
cur = conn.cursor()

# =========================
# MENU
# =========================
if st.session_state.get("logado"):
    menu = st.sidebar.selectbox(
        "Menu",
        [
            "Cadastrar Linha",
            "Editar Linha",
            "Cadastrar / Editar Final de Linha",
            "Consultar Linhas"
        ]
    )
else:
    menu = "Consultar Linhas"

# =========================
# CADASTRAR LINHA
# =========================
if menu == "Cadastrar Linha":
    st.header("Cadastrar Linha")

    codigo = st.text_input("Código da linha")
    nome = st.text_input("Nome da linha")

    if st.button("Salvar"):
        try:
            cur.execute(
                "INSERT INTO linha (codigo_linha, nome_linha) VALUES (%s, %s)",
                (codigo, nome)
            )
            conn.commit()
            st.success("Linha cadastrada com sucesso!")
        except Exception:
            conn.rollback()
            st.error("Erro ao cadastrar. Código pode já existir.")

# =========================
# EDITAR LINHA
# =========================
elif menu == "Editar Linha":
    st.header("Editar Linha")

    cur.execute("""
        SELECT id, codigo_linha, nome_linha, ativa
        FROM linha
        ORDER BY codigo_linha
    """)
    linhas = cur.fetchall()

    linha = st.selectbox(
        "Linha",
        linhas,
        format_func=lambda x: f"{x[1]} - {x[2]}"
    )

    linha_id = linha[0]

    codigo_atual = linha[1]
    nome_atual = linha[2]
    ativa_atual = linha[3]

    codigo = st.text_input("Código da linha", value=codigo_atual)
    nome = st.text_input("Nome da linha", value=nome_atual)
    ativa = st.checkbox("Linha ativa", value=ativa_atual)

    if st.button("Salvar alterações"):
        try:
            cur.execute(
                """
                UPDATE linha
                SET codigo_linha = %s,
                    nome_linha = %s,
                    ativa = %s
                WHERE id = %s
                """,
                (codigo, nome, ativa, linha_id)
            )
            conn.commit()
            st.success("Linha atualizada com sucesso!")
        except Exception:
            conn.rollback()
            st.error("Erro ao salvar. Código pode já existir.")

# =========================
# CADASTRAR / EDITAR FINAL + MAPA
# =========================
elif menu == "Cadastrar / Editar Final de Linha":
    st.header("Cadastrar / Editar Final de Linha")

    cur.execute("SELECT id, codigo_linha FROM linha ORDER BY codigo_linha")
    linhas = cur.fetchall()

    linha = st.selectbox(
        "Linha",
        linhas,
        format_func=lambda x: x[1]
    )

    linha_id = linha[0]

    # 🔍 Buscar dados atuais do final de linha
    cur.execute(
        """
        SELECT rua, bairro, latitude, longitude
        FROM final_linha
        WHERE linha_id = %s
        """,
        (linha_id,)
    )
    final = cur.fetchone()

    rua_atual = final[0] if final else ""
    bairro_atual = final[1] if final else ""
    lat_atual = float(final[2]) if final and final[2] else 0.0
    lon_atual = float(final[3]) if final and final[3] else 0.0

    rua = st.text_input("Rua", value=rua_atual)
    bairro = st.text_input("Bairro", value=bairro_atual)
    latitude = st.number_input("Latitude", value=lat_atual, format="%.6f")
    longitude = st.number_input("Longitude", value=lon_atual, format="%.6f")

    # 🔍 Buscar mapa atual (se existir)
    cur.execute(
        """
        SELECT url_imagem
        FROM mapa_linha
        WHERE linha_id = %s
        """,
        (linha_id,)
    )
    mapa = cur.fetchone()

    if mapa:
        st.markdown("🗺️ **Mapa atual do itinerário:**")
        st.image(mapa[0], use_container_width=True)

    imagem = st.file_uploader(
        "Enviar novo mapa (opcional)",
        type=["png", "jpg", "jpeg"]
    )

    if st.button("Salvar"):
        # FINAL DE LINHA
        cur.execute(
            """
            INSERT INTO final_linha
            (linha_id, rua, bairro, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (linha_id)
            DO UPDATE SET
                rua = EXCLUDED.rua,
                bairro = EXCLUDED.bairro,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude
            """,
            (linha_id, rua, bairro, latitude, longitude)
        )

        # MAPA
        if imagem:
            ext = imagem.name.split(".")[-1]
            nome_arquivo = f"linha_{linha[1]}.{ext}"
            url = upload_imagem(imagem, nome_arquivo)

            cur.execute(
                """
                INSERT INTO mapa_linha (linha_id, url_imagem)
                VALUES (%s, %s)
                ON CONFLICT (linha_id)
                DO UPDATE SET url_imagem = EXCLUDED.url_imagem
                """,
                (linha_id, url)
            )

        conn.commit()
        st.success("Informações atualizadas com sucesso!")

# =========================
# CONSULTA PÚBLICA
# =========================
elif menu == "Consultar Linhas":
    st.header("Consultar Linhas")

    busca = st.text_input(
        "🔎 Pesquisar linha (código ou nome)",
        placeholder="Ex: 007 ou Jardim Europa"
    )

    if busca:
        cur.execute("""
            SELECT l.codigo_linha,
                   l.nome_linha,
                   f.rua,
                   f.bairro,
                   f.latitude,
                   f.longitude,
                   m.url_imagem
            FROM linha l
            LEFT JOIN final_linha f ON f.linha_id = l.id
            LEFT JOIN mapa_linha m ON m.linha_id = l.id
            WHERE l.codigo_linha ILIKE %s
               OR l.nome_linha ILIKE %s
            ORDER BY l.codigo_linha
        """, (f"%{busca}%", f"%{busca}%"))

    else:
        cur.execute("""
            SELECT l.codigo_linha,
                   l.nome_linha,
                   f.rua,
                   f.bairro,
                   f.latitude,
                   f.longitude,
                   m.url_imagem
            FROM linha l
            LEFT JOIN final_linha f ON f.linha_id = l.id
            LEFT JOIN mapa_linha m ON m.linha_id = l.id
            ORDER BY l.codigo_linha
            LIMIT 50
        """)

    resultados = cur.fetchall()

    if not resultados:
        st.warning("Nenhuma linha encontrada.")
    else:
        st.caption(f"{len(resultados)} linha(s) encontrada(s).")

        for codigo, nome, rua, bairro, lat, lon, img in resultados:
            st.subheader(f"Linha {codigo} – {nome}")

            if rua or bairro:
                st.write(f"📍 {rua or ''} - {bairro or ''}")

            if lat and lon:
                maps = f"https://www.google.com/maps?q={lat},{lon}"
                st.link_button("Abrir no Google Maps", maps)

            if img:
                st.image(img, use_container_width=True)

            # HORÁRIOS
            cur.execute(
                """
                SELECT tipo_dia, horario, observacao
                FROM horario_saida hs
                JOIN linha l ON l.id = hs.id_linha
                WHERE l.codigo_linha = %s
                ORDER BY
                    CASE tipo_dia
                        WHEN 'UTIL' THEN 1
                        WHEN 'SABADO' THEN 2
                        WHEN 'DOMINGO' THEN 3
                    END,
                    horario
                """,
                (codigo,)
            )
            
            horarios = cur.fetchall()
            
            if horarios:
                st.markdown("### 🕒 Horários")
            
                dias = {
                    "UTIL": [],
                    "SABADO": [],
                    "DOMINGO": []
                }
            
                for tipo_dia, horario, observacao in horarios:
                    texto = horario.strftime("%H:%M")
            
                    if observacao:
                        texto += f" ({observacao})"
            
                    dias[tipo_dia].append(texto)
            
                if dias["UTIL"]:
                    st.markdown("**Dias Úteis**")
                    st.write(" • ".join(dias["UTIL"]))
            
                if dias["SABADO"]:
                    st.markdown("**Sábados**")
                    st.write(" • ".join(dias["SABADO"]))
            
                if dias["DOMINGO"]:
                    st.markdown("**Domingos**")
                    st.write(" • ".join(dias["DOMINGO"]))
            
            else:
                st.info("Horários ainda não cadastrados.")

            st.divider()
