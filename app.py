import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import unicodedata
from datetime import datetime
import pytz

# --- SISTEMA DE AUTENTICAÇÃO ---
SENHA_CORRETA = "racao123"  # Troque para a senha que vocês vão combinar

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.set_page_config(layout="centered")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Fábrica de Ração")
        st.image("https://cdn-icons-png.flaticon.com/512/1005/1005141.png", width=100)
        senha = st.text_input("Senha de acesso:", type="password", key="senha_input")
        
        if st.button("👉 Entrar no Sistema", use_container_width=True, type="primary"):
            if senha == SENHA_CORRETA:
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
        
        st.info("📞 Solicite acesso ao administrador")
    st.stop()

# --- Função para formatar valores em R$ ---
def br_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- Configuração da página ---
st.set_page_config(
    page_title="Orçamento - Fábrica de Ração", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS para mobile optimization ---
st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
        min-height: 3rem;
        font-size: 1.1rem;
    }
    .stForm {padding: 0.5rem;}
    .dataframe {font-size: 0.85em;}
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        font-size: 1rem; padding: 0.8rem;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .main .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    </style>
""", unsafe_allow_html=True)

# --- Logo e título ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("https://cdn-icons-png.flaticon.com/512/1005/1005141.png", width=80)
    st.title("📊 Sistema de Orçamentos")

# --- 1️⃣ Nome do cliente ---
cliente = st.text_input("Nome do Cliente")

# --- 2️⃣ Produtos ---
try:
    produtos_df = pd.read_excel("produtos.xlsx")
except FileNotFoundError:
    st.warning("Arquivo 'produtos.xlsx' não encontrado. Usando dados de exemplo.")
    produtos_df = pd.DataFrame({
        "Produto": ["Ração Crescimento", "Ração Engorda", "Sal Mineral", "Ração Núcleo", "Convert +@ 1GR"],
        "Valor": [75.50, 82.00, 55.90, 120.00, 86.32]
    })

# --- 3️⃣ DataFrame sessão ---
if "df_calc" not in st.session_state:
    st.session_state.df_calc = pd.DataFrame(columns=[
        "Produto", "Valor", "Frete", "Quantidade", "Desconto", 
        "Frete Total", "Desconto por item", "Total"
    ])

# --- 4️⃣ Adicionar item (sem busca, só selectbox) ---
st.subheader("📝 Adicionar Item")
with st.form("form_item", clear_on_submit=True):
    produtos_lista = produtos_df["Produto"].tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        produto_selecionado = st.selectbox("Produto", produtos_lista, key="produto_select")
        quantidade = st.number_input("Quantidade (sacos)", min_value=1, value=1, key="qtd_input")
    with col2:
        frete = st.number_input("Frete por produto (R$)", min_value=0.0, value=0.0, step=0.5, key="frete_input")
        desconto = st.number_input("Desconto (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="desconto_input")
    
    submitted = st.form_submit_button("➕ Adicionar Item", use_container_width=True)

if submitted:
    valor = float(produtos_df.loc[produtos_df["Produto"] == produto_selecionado, "Valor"].iloc[0])
    total_item = (valor * quantidade) + (frete * quantidade) - (valor * (desconto / 100) * quantidade)
    new_row = {
        "Produto": produto_selecionado,
        "Valor": valor,
        "Frete": frete,
        "Quantidade": quantidade,
        "Desconto": desconto,
        "Frete Total": frete * quantidade,
        "Desconto por item": valor * (desconto / 100) * quantidade,
        "Total": total_item
    }
    st.session_state.df_calc = pd.concat([st.session_state.df_calc, pd.DataFrame([new_row])], ignore_index=True)
    st.success(f"✅ '{produto_selecionado}' adicionado!")
    st.rerun()

# --- 5️⃣ Tabela cumulativa ---
if not st.session_state.df_calc.empty:
    st.subheader("📊 Itens do Orçamento")
    
    if st.button("🗑️ Limpar Todos os Itens", type="secondary", use_container_width=True):
        st.session_state.df_calc = pd.DataFrame(columns=[
            "Produto", "Valor", "Frete", "Quantidade", "Desconto", 
            "Frete Total", "Desconto por item", "Total"
        ])
        st.rerun()
    
    df_display = st.session_state.df_calc.copy()
    for col in ["Valor", "Frete", "Frete Total", "Desconto por item", "Total"]:
        df_display[col] = df_display[col].apply(lambda x: f"{x:.2f}")
    df_display["Quantidade"] = df_display["Quantidade"].apply(lambda x: f"{x} saco(s)")
    df_display["Desconto"] = df_display["Desconto"].apply(lambda x: f"{x}%")
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)

# --- Totais ---
total_produtos = st.session_state.df_calc['Total'].sum() if not st.session_state.df_calc.empty else 0
quantidade_total = st.session_state.df_calc['Quantidade'].sum() if not st.session_state.df_calc.empty else 0
frete_total = st.session_state.df_calc['Frete Total'].sum() if not st.session_state.df_calc.empty else 0

# --- Funções de cálculo (mantidas iguais) ---
def coeficiente_por_prazo(prazo, quantidade_total):
    if prazo == "30":
        if quantidade_total >= 600: return 0.0212940034619435
        elif quantidade_total >= 300: return 0.0272940034619435
        else: return 0.0332940034619435
    elif prazo == "60":
        if quantidade_total >= 600: return 0.0393507895679797
        elif quantidade_total >= 300: return 0.0453507895679797
        else: return 0.0513507895679797
    elif prazo == "15/45":
        if quantidade_total >= 600: return 0.021294003
        elif quantidade_total >= 300: return 0.027294003
        else: return 0.033294003
    elif prazo == "30/60":
        if quantidade_total >= 600: return 0.030248473
        elif quantidade_total >= 300: return 0.036248473
        else: return 0.042248473
    elif prazo == "30/60/90":
        if quantidade_total >= 600: return 0.03935079
        elif quantidade_total >= 300: return 0.04535079
        else: return 0.05135079
    return 0.05

def calcular_valor_prazo(total_produtos, prazo, quantidade_total):
    coef = coeficiente_por_prazo(prazo, quantidade_total)
    return total_produtos * (1 + coef)

# --- Condições ---
condicoes = [
    {"tipo": "A VISTA", "valor_final": total_produtos, "parcelas": 1},
    {"tipo": "PRAZO 30", "valor_final": calcular_valor_prazo(total_produtos, "30", quantidade_total), "parcelas": 1},
    {"tipo": "PRAZO 60", "valor_final": calcular_valor_prazo(total_produtos, "60", quantidade_total), "parcelas": 1},
    {"tipo": "PRAZO 15/45", "valor_final": calcular_valor_prazo(total_produtos, "15/45", quantidade_total), "parcelas": 2},
    {"tipo": "PRAZO 30/60", "valor_final": calcular_valor_prazo(total_produtos, "30/60", quantidade_total), "parcelas": 2},
    {"tipo": "PRAZO 30/60/90", "valor_final": calcular_valor_prazo(total_produtos, "30/60/90", quantidade_total), "parcelas": 3},
]

tabela_prazos = []
for c in condicoes:
    valor_total = c["valor_final"]
    num_parcelas = c["parcelas"]
    if num_parcelas > 1:
        valor_parcela = valor_total / num_parcelas
        texto_parcelas = f"{num_parcelas} x {br_real(valor_parcela)}"
    else:
        texto_parcelas = br_real(valor_total)
    tabela_prazos.append([c["tipo"], br_real(valor_total), texto_parcelas])

st.metric(label="💰 Total Geral (à vista)", value=br_real(total_produtos))
df_prazos = pd.DataFrame(tabela_prazos, columns=["Condição", "Valor Total", "Parcela(s)"])
st.subheader("📅 Condições de Pagamento")
st.dataframe(df_prazos, use_container_width=True, hide_index=True)

# --- Seleção de prazo ---
st.subheader("📄 Configurações do PDF")
prazo_selecionado = st.selectbox(
    "Selecione o prazo para o PDF:",
    options=["A VISTA", "PRAZO 30", "PRAZO 60", "PRAZO 15/45", "PRAZO 30/60", "PRAZO 30/60/90"],
    index=0
)

# --- Gerar PDF ---
if st.button("📄 Gerar PDF do Orçamento", use_container_width=True, type="primary"):
    if st.session_state.df_calc.empty:
        st.warning("Não há itens no orçamento para gerar PDF.")
    elif not cliente:
        st.warning("Por favor, informe o nome do cliente.")
    else:
        valor_prazo_selecionado = next(
            (c["valor_final"] for c in condicoes if c["tipo"] == prazo_selecionado),
            total_produtos
        )
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        elements = []
        styles = getSampleStyleSheet()
        
        title = Paragraph(f"<b>Orçamento - {cliente}</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        data = [["Produto", "Valor Unitário", "Quantidade", "Total"]]
        for _, row in st.session_state.df_calc.iterrows():
            proporcao_prazo = valor_prazo_selecionado / total_produtos if total_produtos > 0 else 1
            valor_unitario_prazo = (row['Total'] / row['Quantidade']) * proporcao_prazo
            data.append([
                row['Produto'],
                br_real(valor_unitario_prazo),
                f"{int(row['Quantidade'])} saco(s)",
                br_real(row['Total'] * proporcao_prazo)
            ])
        
        data.append(["", "", "TOTAL (" + prazo_selecionado + "):", br_real(valor_prazo_selecionado)])
        
        tabela = Table(data, hAlign='CENTER', repeatRows=1)
        tabela_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.whitesmoke, colors.lightgrey]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ])
        tabela.setStyle(tabela_style)
        elements.append(tabela)
        elements.append(Spacer(1, 20))
        
        # Corrigir data/hora Brasil
        fuso_brasil = pytz.timezone("America/Sao_Paulo")
        data_envio = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M")
        
        elements.append(Paragraph(f"<b>Data envio: {data_envio}</b>", styles['Normal']))
        elements.append(Paragraph("<b>* Validade da proposta 5 dias</b>", styles['Normal']))
        elements.append(Paragraph("<b>* Os Preços podem sofrer alterações sem aviso prévio</b>", styles['Normal']))
        
        doc.build(elements)
        buffer.seek(0)
        
        data_arquivo = datetime.now(fuso_brasil).strftime("%d-%m-%Y")
        cliente_sanitizado = "".join(c for c in cliente if c.isalnum() or c in (' ', '-', '_')).rstrip()
        nome_arquivo = f"Orcamento_{cliente_sanitizado}_{data_arquivo}.pdf"
        
        st.download_button(
            label="⬇️ Baixar PDF do Orçamento",
            data=buffer,
            file_name=nome_arquivo,
            mime="application/pdf",
            use_container_width=True
        )
        
                # --- Botão de compartilhamento nativo (Web Share API) ---
        compartilhar_code = f"""
        <script>
        function compartilharPDF() {{
            if (navigator.share) {{
                navigator.share({{
                    title: 'Orçamento',
                    text: 'Segue o orçamento gerado.',
                    url: '{nome_arquivo}'
                }})
                .then(() => console.log('Compartilhado com sucesso'))
                .catch((error) => console.log('Erro ao compartilhar:', error));
            }} else {{
                alert('Compartilhamento não suportado neste dispositivo.');
            }}
        }}
        </script>
        <button onclick="compartilharPDF()" style="
            background-color:#25D366;
            color:white;
            border:none;
            padding:10px 20px;
            font-size:16px;
            border-radius:10px;
            cursor:pointer;
            width:100%;
            margin-top:10px;">
        📤 Compartilhar Orçamento
        </button>
        """

        st.markdown(compartilhar_code, unsafe_allow_html=True)


# --- Logout ---
if st.button("🚪 Sair do Sistema", type="secondary", use_container_width=True):
    st.session_state.logado = False
    st.rerun()

