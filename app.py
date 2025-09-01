import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import locale

# --- SISTEMA DE AUTENTICAÇÃO ---
SENHA_CORRETA = "racao123"  # Troque para a senha que vocês vão combinar

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    # Tela de login otimizada para mobile
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

# --- CONFIGURAÇÃO PRINCIPAL (APÓS LOGIN) ---
# --- Configurar local para português do Brasil ---
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')

# --- Função para formatar valores em R$ ---
def br_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- Configuração da página mobile-friendly ---
st.set_page_config(
    page_title="Orçamento - Fábrica de Ração", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS para mobile optimization ---
st.markdown("""
    <style>
    /* Melhorar toque em botões para mobile */
    .stButton > button {
        width: 100%;
        min-height: 3rem;
        font-size: 1.1rem;
    }
    
    /* Formulários mais compactos */
    .stForm {
        padding: 0.5rem;
    }
    
    /* Melhorar visualização de tabelas no mobile */
    .dataframe {
        font-size: 0.85em;
    }
    
    /* Ajustar inputs para mobile */
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        font-size: 1rem;
        padding: 0.8rem;
    }
    
    /* Esconder menu e rodapé */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Melhor espaçamento geral */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- Logo e título ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("https://cdn-icons-png.flaticon.com/512/1005/1005141.png", width=80)
    st.title("📊 Sistema de Orçamentos")

# --- 1️⃣ Carregar ou criar planilha de produtos ---
try:
    produtos_df = pd.read_excel("produtos.xlsx")
except FileNotFoundError:
    st.warning("Arquivo 'produtos.xlsx' não encontrado. Usando dados de exemplo.")
    produtos_df = pd.DataFrame({
        "Produto": ["Ração Crescimento", "Ração Engorda", "Sal Mineral"],
        "Valor": [75.50, 82.00, 55.90]
    })

with st.expander("📄 Produtos Disponíveis"):
    st.dataframe(produtos_df, use_container_width=True)

# --- 2️⃣ Inicializar DataFrame na sessão ---
if "df_calc" not in st.session_state:
    st.session_state.df_calc = pd.DataFrame(columns=[
        "Produto", "Valor", "Frete", "Quantidade", "Desconto", 
        "Frete Total", "Desconto por item", "Total"
    ])

# --- 3️⃣ Formulário para adicionar item (mobile optimized) ---
st.subheader("📝 Adicionar Item")
with st.form("form_item", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        produto_selecionado = st.selectbox("Produto", produtos_df["Produto"], key="produto_select")
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

# --- 4️⃣ Mostrar tabela cumulativa ---
if not st.session_state.df_calc.empty:
    st.subheader("📊 Itens do Orçamento")
    
    # Botão para limpar tudo
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

# --- Cálculos de totais ---
total_produtos = st.session_state.df_calc['Total'].sum() if not st.session_state.df_calc.empty else 0
quantidade_total = st.session_state.df_calc['Quantidade'].sum() if not st.session_state.df_calc.empty else 0
frete_total = st.session_state.df_calc['Frete Total'].sum() if not st.session_state.df_calc.empty else 0

# --- Função para calcular coeficiente por prazo ---
def coeficiente_por_prazo(prazo, quantidade_total):
    if prazo == "30":
        if quantidade_total >= 600:
            return 0.0212940034619435
        elif quantidade_total >= 300:
            return 0.0272940034619435
        else:
            return 0.0332940034619435
    elif prazo == "60":
        if quantidade_total >= 600:
            return 0.0393507895679797
        elif quantidade_total >= 300:
            return 0.0453507895679797
        else:
            return 0.0513507895679797
    elif prazo == "15/45":
        if quantidade_total >= 600:
            return 0.021294003
        elif quantidade_total >= 300:
            return 0.027294003
        else:
            return 0.033294003
    elif prazo == "30/60":
        if quantidade_total >= 600:
            return 0.030248473
        elif quantidade_total >= 300:
            return 0.036248473
        else:
            return 0.042248473
    elif prazo == "30/60/90":
        if quantidade_total >= 600:
            return 0.03935079
        elif quantidade_total >= 300:
            return 0.04535079
        else:
            return 0.05135079
    return 0.05  # fallback

# --- Função para calcular valor a prazo ---
def calcular_valor_prazo(total_produtos, prazo, quantidade_total):
    coef = coeficiente_por_prazo(prazo, quantidade_total)
    valor_juros = total_produtos * (1 + coef)
    return valor_juros

# --- Condições de pagamento ---
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

# --- Exibir resultados ---
st.metric(label="💰 Total Geral (à vista)", value=br_real(total_produtos))

df_prazos = pd.DataFrame(tabela_prazos, columns=["Condição", "Valor Total", "Parcela(s)"])
st.subheader("📅 Condições de Pagamento")
st.dataframe(df_prazos, use_container_width=True, hide_index=True)

# --- 5️⃣ Botão para gerar PDF premium ---
if st.button("📄 Gerar PDF do Orçamento", use_container_width=True, type="primary"):
    if st.session_state.df_calc.empty:
        st.warning("Não há itens no orçamento para gerar PDF.")
    else:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title = Paragraph("<b>Orçamento - Fábrica de Ração</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Preparar dados da tabela principal
        df_display_pdf = st.session_state.df_calc.copy()
        for col in ["Valor", "Frete", "Frete Total", "Desconto por item", "Total"]:
            df_display_pdf[col] = df_display_pdf[col].apply(br_real)
        df_display_pdf["Quantidade"] = df_display_pdf["Quantidade"].apply(lambda x: f"{x} saco(s)")
        df_display_pdf["Desconto"] = df_display_pdf["Desconto"].apply(lambda x: f"{x}%")
        
        # Criar tabela
        data = [list(df_display_pdf.columns)] + df_display_pdf.values.tolist()
        tabela = Table(data, hAlign='CENTER', repeatRows=1)
        
        # Estilo da tabela
        tabela_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ])
        
        # Destacar itens com valor alto
        for i, row in st.session_state.df_calc.iterrows():
            if row['Total'] > 1000:
                tabela_style.add('BACKGROUND', (0, i + 1), (-1, i + 1), colors.lightcoral)
                tabela_style.add('TEXTCOLOR', (0, i + 1), (-1, i + 1), colors.whitesmoke)
        
        tabela.setStyle(tabela_style)
        elements.append(tabela)
        elements.append(Spacer(1, 20))
        
        # Total geral
        total_paragraph = Paragraph(f"<b>Total Geral (à vista): {br_real(total_produtos)}</b>", styles['Heading2'])
        elements.append(total_paragraph)
        
        # Informações adicionais
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>Quantidade Total: {quantidade_total} saco(s)</b>", styles['Normal']))
        elements.append(Paragraph(f"<b>Frete Total: {br_real(frete_total)}</b>", styles['Normal']))
        
        # Condições de pagamento
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("<b>Condições de Pagamento</b>", styles['Heading2']))
        
        data_prazos_pdf = [["Condição", "Valor Total", "Parcela(s)"]]
        for c in condicoes:
            valor_total = c["valor_final"]
            num_parcelas = c["parcelas"]
            if num_parcelas > 1:
                valor_parcela = valor_total / num_parcelas
                texto_parcelas = f"{num_parcelas} x {br_real(valor_parcela)}"
            else:
                texto_parcelas = br_real(valor_total)
            data_prazos_pdf.append([c["tipo"], br_real(valor_total), texto_parcelas])
        
        tabela_pdf = Table(data_prazos_pdf, hAlign='CENTER', repeatRows=1)
        tabela_pdf.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ]))
        elements.append(tabela_pdf)
        
        # Rodapé
        elements.append(Spacer(1, 20))
        footer = Paragraph("Orçamento gerado automaticamente - Fábrica de Ração", styles['Normal'])
        elements.append(footer)
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Botão de download
        st.download_button(
            label="⬇️ Baixar PDF do Orçamento",
            data=buffer,
            file_name="orcamento.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        st.success("PDF gerado com sucesso!")

# --- Botão de logout ---
if st.button("🚪 Sair do Sistema", type="secondary", use_container_width=True):
    st.session_state.logado = False
    st.rerun()