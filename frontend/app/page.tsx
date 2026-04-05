"use client"

import { useEffect, useMemo, useRef, useState } from "react"

type Message = {
  role: "user" | "assistant"
  content: string
}

type LoggedUser = {
  id: number
  nome: string
  login: string
  empresa?: string | null
}

type ChatItem = {
  id: number
  title: string
  created_at: string
}

const API_BASE = "http://10.20.30.19:8000"

const INITIAL_MESSAGE =
  "Olá, sou a Analista IA do Cyber Team da BluePex. Posso te ajudar com orientações iniciais, dúvidas sobre produtos e triagem técnica."

export default function Home() {
  const [user, setUser] = useState<LoggedUser | null>(null)
  const [loginInput, setLoginInput] = useState("")
  const [loadingLogin, setLoadingLogin] = useState(false)

  const [chats, setChats] = useState<ChatItem[]>([])
  const [activeChatId, setActiveChatId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: INITIAL_MESSAGE,
    },
  ])

  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [loadingChats, setLoadingChats] = useState(false)
  const [creatingChat, setCreatingChat] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)

  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const storedUser = localStorage.getItem("bluepex_user")

    if (storedUser) {
      const parsedUser: LoggedUser = JSON.parse(storedUser)
      setUser(parsedUser)
    }
  }, [])

  useEffect(() => {
    if (!textareaRef.current) return

    textareaRef.current.style.height = "0px"
    const newHeight = Math.min(textareaRef.current.scrollHeight, 180)
    textareaRef.current.style.height = `${newHeight}px`
  }, [input])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading, loadingMessages])

  useEffect(() => {
    if (!user) return
    loadChats(user.id)
  }, [user])

  useEffect(() => {
    if (!user || !activeChatId) return

    localStorage.setItem(
      `bluepex_active_chat_id_${user.id}`,
      String(activeChatId)
    )

    loadMessages(user.id, activeChatId)
  }, [activeChatId, user])

  const activeChat = useMemo(() => {
    return chats.find((chat) => chat.id === activeChatId) || null
  }, [chats, activeChatId])

  async function handleLogin() {
    const login = loginInput.trim()

    if (!login || loadingLogin) return

    setLoadingLogin(true)

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ login }),
      })

      if (!response.ok) {
        throw new Error("Usuário não encontrado")
      }

      const data: LoggedUser = await response.json()
      localStorage.setItem("bluepex_user", JSON.stringify(data))
      setUser(data)
    } catch {
      alert("Usuário não encontrado ou backend indisponível.")
    } finally {
      setLoadingLogin(false)
    }
  }

  function handleLogout() {
    localStorage.removeItem("bluepex_user")
    setUser(null)
    setChats([])
    setActiveChatId(null)
    setMessages([
      {
        role: "assistant",
        content: INITIAL_MESSAGE,
      },
    ])
    setInput("")
    setLoginInput("")
  }

  async function loadChats(userId: number) {
    setLoadingChats(true)

    try {
      const response = await fetch(`${API_BASE}/users/${userId}/chats`)

      if (!response.ok) {
        throw new Error("Erro ao carregar chats")
      }

      const data: ChatItem[] = await response.json()

      if (data.length === 0) {
        const createResponse = await fetch(`${API_BASE}/chats`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            user_id: userId,
          }),
        })

        if (!createResponse.ok) {
          throw new Error("Erro ao criar primeiro chat")
        }

        const created: { chat_id: number } = await createResponse.json()

        const reloadResponse = await fetch(`${API_BASE}/users/${userId}/chats`)

        if (!reloadResponse.ok) {
          throw new Error("Erro ao recarregar chats")
        }

        const reloadData: ChatItem[] = await reloadResponse.json()
        setChats(reloadData)
        setActiveChatId(created.chat_id)
        return
      }

      setChats(data)

      const storedActiveChatId = localStorage.getItem(
        `bluepex_active_chat_id_${userId}`
      )
      const storedChatId = storedActiveChatId ? Number(storedActiveChatId) : null

      if (storedChatId && data.some((chat) => chat.id === storedChatId)) {
        setActiveChatId(storedChatId)
      } else {
        setActiveChatId(data[0].id)
      }
    } catch {
      alert("Não foi possível carregar os chats do usuário.")
    } finally {
      setLoadingChats(false)
    }
  }

  async function createNewChat() {
    if (!user || creatingChat) return

    setCreatingChat(true)

    try {
      const response = await fetch(`${API_BASE}/chats`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user.id,
        }),
      })

      if (!response.ok) {
        throw new Error("Erro ao criar chat")
      }

      const data: { chat_id: number } = await response.json()

      await loadChats(user.id)
      setActiveChatId(data.chat_id)
    } catch {
      alert("Não foi possível criar um novo chat.")
    } finally {
      setCreatingChat(false)
    }
  }

  async function loadMessages(userId: number, chatId: number) {
    setLoadingMessages(true)

    try {
      const response = await fetch(
        `${API_BASE}/chats/${chatId}/messages?user_id=${userId}`
      )

      if (!response.ok) {
        throw new Error("Erro ao carregar histórico")
      }

      const data: { messages: Message[] } = await response.json()

      if (data.messages && data.messages.length > 0) {
        setMessages(data.messages)
      } else {
        setMessages([
          {
            role: "assistant",
            content: INITIAL_MESSAGE,
          },
        ])
      }
    } catch {
      setMessages([
        {
          role: "assistant",
          content: "Não foi possível carregar o histórico deste chat.",
        },
      ])
    } finally {
      setLoadingMessages(false)
    }
  }

  async function sendMessage() {
    const texto = input.trim()

    if (!texto || loading || !user || !activeChatId) return

    const novasMensagens: Message[] = [
      ...messages,
      { role: "user", content: texto },
    ]

    setMessages(novasMensagens)
    setInput("")
    setLoading(true)

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user.id,
          chat_id: activeChatId,
          message: texto,
        }),
      })

      const data = await response.json()

      setMessages([
        ...novasMensagens,
        {
          role: "assistant",
          content: data.response || "Sem resposta do backend.",
        },
      ])

      await loadChats(user.id)
    } catch {
      setMessages([
        ...novasMensagens,
        {
          role: "assistant",
          content: "Não foi possível conectar ao servidor no momento.",
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function resetChat() {
    if (!user || !activeChatId) return

    try {
      const response = await fetch(`${API_BASE}/chat/reset`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user.id,
          chat_id: activeChatId,
        }),
      })

      if (!response.ok) {
        throw new Error("Erro ao resetar chat")
      }

      setMessages([
        {
          role: "assistant",
          content: INITIAL_MESSAGE,
        },
      ])
    } catch {
      alert("Não foi possível resetar este chat.")
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (!user) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950 px-4 text-white">
        <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-900 p-6 shadow-lg">
          <div className="mb-6">
            <h1 className="text-xl font-semibold">Cyber Team IA</h1>
            <p className="mt-2 text-sm text-zinc-400">
              Faça login para acessar seu painel de atendimento e conversas.
            </p>
          </div>

          <div className="space-y-3">
            <label className="block text-sm font-medium text-zinc-300">
              Login do usuário
            </label>

            <input
              value={loginInput}
              onChange={(e) => setLoginInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleLogin()
                }
              }}
              placeholder="Ex.: leonardo"
              className="w-full rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-3 text-sm text-white outline-none placeholder:text-zinc-500"
            />

            <button
              onClick={handleLogin}
              disabled={loadingLogin || !loginInput.trim()}
              className="w-full rounded-xl bg-blue-600 px-4 py-3 font-medium transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loadingLogin ? "Entrando..." : "Entrar"}
            </button>
          </div>

          <p className="mt-4 text-xs text-zinc-500">
            Login fake para testes do painel multiusuário.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-zinc-950 text-white">
      <aside className="hidden w-80 border-r border-zinc-800 bg-zinc-900/95 md:flex md:flex-col">
        <div className="border-b border-zinc-800 p-4">
          <button
            onClick={createNewChat}
            disabled={creatingChat}
            className="w-full rounded-xl bg-blue-600 px-4 py-3 text-left font-medium transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {creatingChat ? "Criando..." : "+ Novo chat"}
          </button>

          <div className="mt-4">
            <div className="text-sm font-semibold text-white">Cyber Team IA</div>
            <div className="text-xs text-zinc-400">
              Analista virtual para triagem e orientação inicial
            </div>

            <div className="mt-3 rounded-xl border border-zinc-800 bg-zinc-950/60 p-3">
              <div className="text-xs font-semibold text-zinc-300">{user.nome}</div>
              <div className="text-xs text-zinc-500">{user.login}</div>
              {user.empresa && (
                <div className="mt-1 text-xs text-zinc-400">{user.empresa}</div>
              )}

              <button
                onClick={handleLogout}
                className="mt-3 text-xs font-medium text-red-400 transition hover:text-red-300"
              >
                Sair
              </button>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <div className="mb-3 px-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            Conversas
          </div>

          {loadingChats ? (
            <div className="px-2 text-sm text-zinc-400">Carregando chats...</div>
          ) : chats.length === 0 ? (
            <div className="px-2 text-sm text-zinc-500">
              Nenhum chat criado ainda.
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {chats.map((chat) => {
                const isActive = chat.id === activeChatId

                return (
                  <button
                    key={chat.id}
                    onClick={() => setActiveChatId(chat.id)}
                    className={`rounded-xl border px-3 py-3 text-left transition ${
                      isActive
                        ? "border-blue-500 bg-zinc-800"
                        : "border-zinc-800 bg-zinc-900 hover:bg-zinc-800"
                    }`}
                  >
                    <div className="truncate text-sm font-medium text-white">
                      {chat.title}
                    </div>
                    <div className="mt-1 text-xs text-zinc-400">
                      {new Date(chat.created_at).toLocaleString("pt-BR")}
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </aside>

      <main className="flex flex-1 flex-col">
        <header className="border-b border-zinc-800 bg-zinc-950/90 px-4 py-4 md:px-8">
          <div className="mx-auto flex max-w-5xl items-start justify-between gap-4">
            <div>
              <h1 className="text-lg font-semibold">Analista IA do Cyber Team</h1>
              <p className="text-sm text-zinc-400">
                Triagem técnica inicial e orientação sobre soluções BluePex
              </p>
              <div className="mt-1 text-xs text-zinc-500">
                Logado como: {user.nome} ({user.login})
              </div>
            </div>

            <div className="flex gap-2">
              {activeChat && (
                <button
                  onClick={resetChat}
                  className="rounded-xl border border-zinc-700 px-3 py-2 text-sm transition hover:bg-zinc-800"
                >
                  Resetar chat
                </button>
              )}

              <button
                onClick={handleLogout}
                className="rounded-xl border border-zinc-700 px-3 py-2 text-sm transition hover:bg-zinc-800"
              >
                Sair
              </button>
            </div>
          </div>
        </header>

        <section className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <div className="mx-auto flex max-w-5xl flex-col gap-4">
            {loadingMessages ? (
              <div className="max-w-[90%] rounded-2xl bg-zinc-800 px-4 py-4 shadow-sm">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-300">
                  Analista IA
                </div>
                <div className="text-sm text-zinc-300">Carregando histórico...</div>
              </div>
            ) : (
              messages.map((msg, index) => (
                <div
                  key={index}
                  className={`rounded-2xl px-4 py-4 shadow-sm ${
                    msg.role === "user"
                      ? "ml-auto w-fit max-w-[85%] bg-blue-600"
                      : "max-w-[90%] bg-zinc-800"
                  }`}
                >
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-300">
                    {msg.role === "user" ? "Você" : "Analista IA"}
                  </div>

                  <div className="whitespace-pre-wrap break-words text-sm leading-7 text-zinc-100">
                    {msg.content}
                  </div>
                </div>
              ))
            )}

            {loading && (
              <div className="max-w-[90%] rounded-2xl bg-zinc-800 px-4 py-4 shadow-sm">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-300">
                  Analista IA
                </div>
                <div className="text-sm text-zinc-300">Analisando sua solicitação...</div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </section>

        <footer className="border-t border-zinc-800 bg-zinc-950/90 px-4 py-4 md:px-8">
          <div className="mx-auto max-w-5xl">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-3 shadow-sm">
              <div className="flex items-end gap-3">
                <textarea
                  ref={textareaRef}
                  rows={1}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={!activeChatId || loading}
                  placeholder={
                    activeChatId
                      ? "Descreva sua solicitação. Enter envia, Shift + Enter quebra linha."
                      : "Criando ou selecionando um chat..."
                  }
                  className="max-h-[180px] min-h-[52px] flex-1 resize-none overflow-y-auto rounded-xl bg-transparent px-3 py-3 text-sm text-white outline-none placeholder:text-zinc-500 disabled:opacity-60"
                />

                <button
                  onClick={sendMessage}
                  disabled={loading || !input.trim() || !activeChatId}
                  className="rounded-xl bg-blue-600 px-5 py-3 font-medium transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Enviar
                </button>
              </div>
            </div>

            <p className="mt-2 text-xs text-zinc-500">
              Esta interface é destinada à demonstração de triagem e orientação inicial.
            </p>
          </div>
        </footer>
      </main>
    </div>
  )
} 
