import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
from dotenv import load_dotenv

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "conhecimento"

RULES_DIR = KNOWLEDGE_DIR / "00_regras"
PRODUCTS_DIR = KNOWLEDGE_DIR / "01_produtos"
DOCS_DIR = KNOWLEDGE_DIR / "02_documentacao"
PROCESSED_DIR = KNOWLEDGE_DIR / "03_processado"

INDEX_FILE = PROCESSED_DIR / "pdf_index.json"

TERMOS_PROIBIDOS = [
    "pfsense",
    "squid",
    "suricata",
    "cloudberry",
    "white label",
    "white-label",
    "oem",
    "engine",
    "fork",
    "baseado em",
]

PALAVRAS_IRRELEVANTES = {
    "de", "da", "do", "das", "dos", "a", "o", "e", "em", "para", "por", "com",
    "um", "uma", "no", "na", "nos", "nas", "ao", "aos", "ou", "que", "como",
    "se", "ser", "é", "são", "já", "mais", "menos", "não", "sim", "sobre",
    "uma", "uns", "umas", "os", "as", "me", "te", "lhe", "isso", "isto",
    "esse", "essa", "qual", "quais", "onde", "quando", "porque", "pra"
}


def normalizar_texto(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r"[^\w\sÀ-ÿ-]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def tokenizar(texto: str) -> List[str]:
    texto = normalizar_texto(texto)
    return [t for t in texto.split() if len(t) > 2 and t not in PALAVRAS_IRRELEVANTES]


def ler_arquivo_texto(caminho: Path) -> str:
    if not caminho.exists():
        return ""
    return caminho.read_text(encoding="utf-8", errors="ignore").strip()


def carregar_regras() -> str:
    partes = []
    if not RULES_DIR.exists():
        return ""

    for arquivo in sorted(RULES_DIR.glob("*.txt")):
        conteudo = ler_arquivo_texto(arquivo)
        if conteudo:
            partes.append(f"### {arquivo.stem}\n{conteudo}")

    return "\n\n".join(partes)


def detectar_produto(pergunta: str) -> Optional[str]:
    p = normalizar_texto(pergunta)

    if any(x in p for x in ["cyberdomo", "endpoint", "compliance", "documento", "documentos", "cloud suite"]):
        return "cyberdomo"

    if any(x in p for x in ["firewall", "nat", "regra", "wan", "lan", "opt", "vpn"]):
        return "firewall"

    if any(x in p for x in ["backup", "restauracao", "restauração", "restore", "retenção", "retencao"]):
        return "backup"

    if any(x in p for x in ["email", "e-mail", "smtp", "imap", "pop", "dkim", "spf", "antispam"]):
        return "email"

    return None


def carregar_contexto_produto(produto: Optional[str]) -> str:
    if not produto:
        return ""

    pasta = PRODUCTS_DIR / produto
    if not pasta.exists():
        return ""

    partes = []
    for arquivo in sorted(pasta.glob("*.txt")):
        conteudo = ler_arquivo_texto(arquivo)
        if conteudo:
            partes.append(f"### {produto}/{arquivo.stem}\n{conteudo}")

    return "\n\n".join(partes)


def extrair_texto_pdf(pdf_path: Path) -> str:
    if PdfReader is None:
        raise RuntimeError("Biblioteca pypdf não encontrada. Instale com: pip install pypdf")

    reader = PdfReader(str(pdf_path))
    paginas = []

    for i, pagina in enumerate(reader.pages, start=1):
        try:
            texto = pagina.extract_text() or ""
        except Exception:
            texto = ""

        texto = re.sub(r"\s+", " ", texto).strip()
        if texto:
            paginas.append(f"[PÁGINA {i}] {texto}")

    return "\n".join(paginas)


def quebrar_em_chunks(texto: str, chunk_size: int = 1400, overlap: int = 250) -> List[str]:
    texto = re.sub(r"\s+", " ", texto).strip()
    if not texto:
        return []

    chunks = []
    inicio = 0
    tamanho = len(texto)

    while inicio < tamanho:
        fim = min(inicio + chunk_size, tamanho)
        chunk = texto[inicio:fim].strip()
        if chunk:
            chunks.append(chunk)

        if fim >= tamanho:
            break

        inicio = max(fim - overlap, 0)

    return chunks


def obter_manifesto_pdfs() -> List[Dict[str, Any]]:
    manifesto = []

    if not DOCS_DIR.exists():
        return manifesto

    for produto_dir in sorted(DOCS_DIR.iterdir()):
        if not produto_dir.is_dir():
            continue

        pdf_dir = produto_dir / "pdfs"
        if not pdf_dir.exists():
            continue

        for pdf_path in sorted(pdf_dir.glob("*.pdf")):
            stat = pdf_path.stat()
            manifesto.append({
                "produto": produto_dir.name,
                "arquivo": pdf_path.name,
                "mtime": stat.st_mtime,
                "size": stat.st_size,
            })

    return manifesto


def construir_indice_pdfs() -> Dict[str, Any]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    documentos = []
    manifesto = obter_manifesto_pdfs()

    for item in manifesto:
        produto = item["produto"]
        pdf_path = DOCS_DIR / produto / "pdfs" / item["arquivo"]

        try:
            texto = extrair_texto_pdf(pdf_path)
        except Exception as e:
            print(f"[PDF] Falha ao processar {pdf_path.name}: {e}")
            continue

        chunks = quebrar_em_chunks(texto)

        for i, chunk in enumerate(chunks):
            documentos.append({
                "produto": produto,
                "arquivo": item["arquivo"],
                "chunk_id": i,
                "texto": chunk,
                "tokens": tokenizar(chunk),
            })

    indice = {
        "manifesto": manifesto,
        "documentos": documentos,
    }

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False)

    return indice


def carregar_indice_pdfs() -> Dict[str, Any]:
    manifesto_atual = obter_manifesto_pdfs()

    if not INDEX_FILE.exists():
        return construir_indice_pdfs()

    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            indice = json.load(f)
    except Exception:
        return construir_indice_pdfs()

    manifesto_salvo = indice.get("manifesto", [])
    if manifesto_salvo != manifesto_atual:
        return construir_indice_pdfs()

    return indice


def buscar_trechos_relevantes(
    pergunta: str,
    produto: Optional[str] = None,
    limite: int = 4
) -> List[Dict[str, Any]]:
    if not INDEX_PDFS.get("documentos"):
        return []

    tokens_pergunta = set(tokenizar(pergunta))
    if not tokens_pergunta:
        return []

    resultados = []

    for doc in INDEX_PDFS["documentos"]:
        if produto and doc["produto"] != produto:
            continue

        tokens_doc = set(doc.get("tokens", []))
        intersecao = tokens_pergunta.intersection(tokens_doc)
        score = len(intersecao)

        if score > 0:
            resultados.append({
                "score": score,
                "produto": doc["produto"],
                "arquivo": doc["arquivo"],
                "chunk_id": doc["chunk_id"],
                "texto": doc["texto"],
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:limite]


def montar_contexto_pdf(pergunta: str, produto: Optional[str]) -> str:
    trechos = buscar_trechos_relevantes(pergunta, produto=produto, limite=4)
    if not trechos:
        return ""

    partes = []
    for item in trechos:
        partes.append(
            f"### PDF {item['produto']}/{item['arquivo']} | trecho {item['chunk_id']} | score={item['score']}\n"
            f"{item['texto']}"
        )

    return "\n\n".join(partes)


def validar_resposta(resposta: str) -> str:
    resposta_lower = resposta.lower()

    for termo in TERMOS_PROIBIDOS:
        if termo in resposta_lower:
            return (
                "Posso te ajudar com a solução BluePex do seu ambiente. "
                "Para seguirmos com segurança, me informe por favor o sintoma observado, "
                "a mensagem exibida e o ponto exato da configuração em que você está."
            )

    return resposta


REGRAS_GERAIS = carregar_regras()
INDEX_PDFS = carregar_indice_pdfs()


SYSTEM_PROMPT_BASE = f"""
Você é um assistente do Cyber Team da BluePex.

Sua função é orientar clientes, realizar triagem inicial, explicar funcionalidades documentadas e apoiar configurações com segurança.

Regras obrigatórias:
- Responder de forma objetiva, profissional, clara e natural.
- Se apresentar como parte do Cyber Team da BluePex.
- Nunca utilizar o termo "suporte". Sempre utilizar "Cyber Team".
- Nunca expor tecnologia interna, fornecedor original, OEM, white label, engine ou arquitetura subjacente.
- Nunca afirmar ou insinuar que a solução BluePex utiliza tecnologias de terceiros.
- Nunca mencionar pfSense, Squid, Suricata, CloudBerry ou equivalentes.
- Nunca orientar cliente a usar SSH, terminal, linha de comando ou instalação de pacotes.
- Nunca inventar diagnóstico definitivo sem evidências.
- Nunca inventar menus, caminhos de tela ou nomes de botões não documentados.
- Se um procedimento não estiver documentado, orientar de forma conceitual e segura.
- Quando faltar contexto, fazer perguntas curtas, úteis e objetivas.
- Se houver risco operacional, ausência de documentação suficiente ou necessidade de aprofundamento, sinalizar continuidade pelo Cyber Team.

Comportamento esperado:
- Priorizar informações documentadas da base local.
- Tratar os produtos como soluções BluePex.
- Em firewall, não assumir que a interface segue padrões de outras soluções do mercado.
- Mesmo que reconheça similaridade técnica, não deve inferir menus nem estrutura de navegação.
- Se houver documentação de PDF relevante, usá-la como apoio para responder.
- Não ler todos os PDFs sempre; considerar apenas o contexto relevante recuperado.

Base de regras:
{REGRAS_GERAIS}
""".strip()


def montar_messages(
    mensagem_usuario: str,
    historico: Optional[List[Dict[str, str]]] = None
) -> List[Dict[str, str]]:
    produto = detectar_produto(mensagem_usuario)
    contexto_produto = carregar_contexto_produto(produto)
    contexto_pdf = montar_contexto_pdf(mensagem_usuario, produto)

    contexto_dinamico_partes = []

    if produto:
        contexto_dinamico_partes.append(f"Produto detectado: {produto}")

    if contexto_produto:
        contexto_dinamico_partes.append(f"Contexto do produto:\n{contexto_produto}")

    if contexto_pdf:
        contexto_dinamico_partes.append(f"Trechos relevantes de documentação PDF:\n{contexto_pdf}")

    contexto_dinamico = "\n\n".join(contexto_dinamico_partes).strip()

    messages = [{"role": "system", "content": SYSTEM_PROMPT_BASE}]

    if contexto_dinamico:
        messages.append({
            "role": "system",
            "content": f"Contexto adicional para esta conversa:\n\n{contexto_dinamico}"
        })

    if historico:
        messages.extend(historico)

    messages.append({"role": "user", "content": mensagem_usuario})
    return messages


def chamar_modelo(messages: list, temperature: float = 0.3) -> str:
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY não foi definida no arquivo .env")

    url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=90)
    response.raise_for_status()

    data = response.json()
    resposta = data["choices"][0]["message"]["content"].strip()
    return validar_resposta(resposta)


def perguntar_ia_com_historico(historico: list, mensagem: str) -> str:
    messages = montar_messages(mensagem, historico=historico)

    print(f"[IA] Pergunta livre: {mensagem}")
    resposta = chamar_modelo(messages, temperature=0.3)
    print(f"[IA] Resposta livre: {resposta}")

    return resposta


def perguntar_ia(mensagem: str) -> str:
    return perguntar_ia_com_historico([], mensagem)


def reformular_pergunta_fluxo(categoria: str, pergunta_base: str, dados_ja_coletados: dict) -> str:
    prompt = (
        f"Categoria do atendimento: {categoria}\n"
        f"Dados já coletados: {dados_ja_coletados}\n"
        f"Pergunta base: {pergunta_base}\n\n"
        "Reescreva essa pergunta para o cliente de forma natural, curta, profissional e adequada para chat. "
        "Não invente novas perguntas. Apenas reformule a pergunta base."
    )

    messages = montar_messages(prompt)
    return chamar_modelo(messages, temperature=0.2)


def gerar_resumo_profissional(categoria: str, dados_coletados: dict) -> str:
    prompt = (
        f"Categoria: {categoria}\n"
        f"Dados coletados: {dados_coletados}\n\n"
        "Gere um resumo técnico e profissional de triagem para encaminhamento interno. "
        "Seja objetivo. Não cite tecnologia interna. "
        "Estruture de forma clara para o Cyber Team continuar o atendimento."
    )

    messages = montar_messages(prompt)
    return chamar_modelo(messages, temperature=0.2)


if __name__ == "__main__":
    print("Teste rápido da IA BluePex")
    while True:
        pergunta = input("\nPergunta: ").strip()
        if pergunta.lower() in {"sair", "exit", "quit"}:
            break
        try:
            print("\nResposta:\n")
            print(perguntar_ia(pergunta))
        except Exception as e:
            print(f"Erro: {e}")
