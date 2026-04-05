def identificar_categoria(mensagem: str) -> str:
    msg = mensagem.lower()

    if "vpn" in msg:
        return "vpn"

    if "backup" in msg or "cloudberry" in msg or "restore" in msg or "restauração" in msg:
        return "backup"

    if (
        "email" in msg
        or "e-mail" in msg
        or "mail" in msg
        or "smtp" in msg
        or "imap" in msg
        or "pop" in msg
        or "antispam" in msg
        or "caixa postal" in msg
    ):
        return "email"

    return "geral"


FLUXOS = {
    "vpn": {
        "titulo": "Falha de VPN",
        "campos": [
            ("cliente_unidade", "Qual cliente, unidade ou conexão está sendo afetada?"),
            ("escopo", "Isso afeta um usuário específico ou mais pessoas?"),
            ("usuario_nome", "Qual usuário ou usuários estão afetados?"),
            ("erro", "Qual mensagem de erro aparece ao conectar?"),
            ("horario", "Desde que horário o problema começou?"),
        ],
    },
    "email": {
        "titulo": "Falha de E-mail",
        "campos": [
            ("tipo_falha", "O problema é no envio, no recebimento ou em ambos?"),
            ("dominio_conta", "Qual domínio, conta de e-mail ou caixa postal está afetada?"),
            ("escopo", "Isso afeta apenas uma conta ou várias contas?"),
            ("erro", "Qual mensagem de erro aparece?"),
            ("horario", "Desde que horário isso começou?"),
        ],
    },
    "backup": {
        "titulo": "Falha de Backup",
        "campos": [
            ("equipamento_job", "Qual servidor, máquina ou job de backup está com problema?"),
            ("tipo_falha", "A falha ocorre no backup, na restauração ou na conectividade?"),
            ("escopo", "Isso afeta apenas um job ou vários?"),
            ("erro", "Qual mensagem de erro aparece no backup?"),
            ("horario", "Desde que horário isso começou?"),
        ],
    },
}


def iniciar_estado(categoria: str) -> dict:
    return {
        "categoria": categoria,
        "etapa": 0,
        "dados": {},
    }


def obter_pergunta_base_atual(estado: dict) -> str:
    categoria = estado["categoria"]

    if categoria not in FLUXOS:
        return "Pode me descrever melhor o problema para que eu direcione corretamente?"

    fluxo = FLUXOS[categoria]
    etapa = estado["etapa"]

    if etapa >= len(fluxo["campos"]):
        return ""

    return fluxo["campos"][etapa][1]


def registrar_resposta(estado: dict, resposta_cliente: str) -> dict:
    categoria = estado["categoria"]
    fluxo = FLUXOS[categoria]
    etapa = estado["etapa"]

    if etapa >= len(fluxo["campos"]):
        return estado

    campo = fluxo["campos"][etapa][0]
    estado["dados"][campo] = resposta_cliente.strip()
    estado["etapa"] += 1

    return estado


def fluxo_concluido(estado: dict) -> bool:
    categoria = estado["categoria"]

    if categoria not in FLUXOS:
        return False

    return estado["etapa"] >= len(FLUXOS[categoria]["campos"])


def gerar_resumo_bruto(estado: dict) -> str:
    categoria = estado["categoria"]
    fluxo = FLUXOS[categoria]

    linhas = [f"Resumo da triagem - {fluxo['titulo']}"]

    for campo, _ in fluxo["campos"]:
        valor = estado["dados"].get(campo, "não informado")
        linhas.append(f"- {campo}: {valor}")

    return "\n".join(linhas)

