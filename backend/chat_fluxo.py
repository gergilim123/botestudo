from fluxos import (
    identificar_categoria,
    iniciar_estado,
    obter_pergunta_atual,
    registrar_resposta,
    fluxo_concluido,
    gerar_resumo,
)

estado = None

print("=== CHAT DE TRIAGEM BLUEPEX ===")
print("Digite 'sair' para encerrar.\n")

while True:
    mensagem = input("Cliente: ").strip()

    if mensagem.lower() in ["sair", "exit", "quit"]:
        print("Encerrando chat.")
        break

    if estado is None:
        categoria = identificar_categoria(mensagem)

        if categoria == "geral":
            print("\nSuporte: Entendi. Pode me informar se o problema está relacionado a VPN, e-mail ou backup?\n")
            continue

        estado = iniciar_estado(categoria)

        print(f"\nSuporte: Entendi. Vamos iniciar a triagem de {categoria.upper()}.\n")
        print(f"Suporte: {obter_pergunta_atual(estado)}\n")
        continue

    estado = registrar_resposta(estado, mensagem)

    if fluxo_concluido(estado):
        resumo = gerar_resumo(estado)

        print("\nSuporte: Obrigado. Concluí a coleta inicial.\n")
        print(resumo)
        print("\nSuporte: Esse resumo já pode ser encaminhado para o atendimento técnico.\n")

        estado = None
        print("=== NOVO ATENDIMENTO ===\n")
    else:
        print(f"\nSuporte: {obter_pergunta_atual(estado)}\n")

