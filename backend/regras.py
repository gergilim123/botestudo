from ia import perguntar_ia


def processar_mensagem(cliente: str, mensagem: str) -> str:

    mensagem_lower = mensagem.lower()

    # regras simples primeiro
    if "senha" in mensagem_lower:
        return (
            f"Olá {cliente}. Entendi que pode ser um problema de senha. "
            "Você pode me informar qual sistema está apresentando erro?"
        )

    if "internet" in mensagem_lower:
        return (
            f"Olá {cliente}. A internet parou totalmente ou apenas alguns serviços não funcionam?"
        )

    if "vpn" in mensagem_lower:
        return (
            f"Olá {cliente}. Você pode me informar qual unidade ou usuário está tentando conectar na VPN?"
        )

    # se nenhuma regra for encontrada → usa IA
    resposta_ia = perguntar_ia(mensagem)

    return resposta_ia

