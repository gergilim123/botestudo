from fluxos import (
    identificar_categoria,
    iniciar_estado,
    obter_pergunta_base_atual,
    registrar_resposta,
    fluxo_concluido,
    gerar_resumo_bruto,
)
from ia import (
    perguntar_ia_com_historico,
    reformular_pergunta_fluxo,
    gerar_resumo_profissional,
)

historico_livre = []
estado = None

print("=== CHAT DE TRIAGEM BLUEPEX | MODO PROVA DE FOGO ===")
print("Assuntos cobertos com fluxo guiado: VPN, E-mail e Backup")
print("Digite 'sair' para encerrar.\n")

while True:
    mensagem = input("Cliente: ").strip()

    if mensagem.lower() in ["sair", "exit", "quit"]:
        print("Encerrando chat.")
        break

    if not mensagem:
        continue

    if estado is None:
        categoria = identificar_categoria(mensagem)

        if categoria == "geral":
            resposta = perguntar_ia_com_historico(historico_livre, mensagem)
            print(f"\nSuporte: {resposta}\n")

            historico_livre.append({"role": "user", "content": mensagem})
            historico_livre.append({"role": "assistant", "content": resposta})
            continue

        estado = iniciar_estado(categoria)

        abertura = {
            "vpn": "Entendi. Vamos iniciar a triagem da sua VPN.",
            "email": "Entendi. Vamos iniciar a triagem do seu e-mail.",
            "backup": "Entendi. Vamos iniciar a triagem do seu backup.",
        }.get(categoria, "Entendi. Vamos iniciar a triagem.")

        pergunta_base = obter_pergunta_base_atual(estado)
        pergunta_natural = reformular_pergunta_fluxo(
            categoria=estado["categoria"],
            pergunta_base=pergunta_base,
            dados_ja_coletados=estado["dados"],
        )

        print(f"\nSuporte: {abertura}")
        print(f"Suporte: {pergunta_natural}\n")
        continue

    estado = registrar_resposta(estado, mensagem)

    if fluxo_concluido(estado):
        resumo_bruto = gerar_resumo_bruto(estado)
        resumo_profissional = gerar_resumo_profissional(
            categoria=estado["categoria"],
            dados_coletados=estado["dados"],
        )

        print("\nSuporte: Obrigado. Concluí a coleta inicial do atendimento.\n")
        print("=== RESUMO BRUTO ===")
        print(resumo_bruto)
        print("\n=== RESUMO PROFISSIONAL ===")
        print(resumo_profissional)
        print("\nSuporte: Esse atendimento já pode ser encaminhado com o resumo acima.\n")

        estado = None
        historico_livre = []
        print("=== NOVO ATENDIMENTO ===\n")
        continue

    pergunta_base = obter_pergunta_base_atual(estado)
    pergunta_natural = reformular_pergunta_fluxo(
        categoria=estado["categoria"],
        pergunta_base=pergunta_base,
        dados_ja_coletados=estado["dados"],
    )

    print(f"\nSuporte: {pergunta_natural}\n")

