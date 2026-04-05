from ia import perguntar_ia_com_historico

historico = []

print("=== CHAT SUPORTE BLUEPEX ===")
print("Digite 'sair' para encerrar\n")

while True:

    mensagem = input("Cliente: ").strip()

    if mensagem.lower() in ["sair", "exit"]:
        break

    resposta = perguntar_ia_com_historico(historico, mensagem)

    print("\nSuporte:", resposta, "\n")

    historico.append({
        "role": "user",
        "content": mensagem
    })

    historico.append({
        "role": "assistant",
        "content": resposta
    })

