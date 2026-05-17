/* VSNT RAG — chat interface (vanilla JS, no external deps) */

const input   = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");
const msgBox  = document.getElementById("chatMessages");

function scrollDown() { msgBox.scrollTop = msgBox.scrollHeight; }

function appendMsg(role, text, sources) {
  const wrap = document.createElement("div");
  wrap.className = "chat-msg " + role;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrap.appendChild(bubble);

  if (sources && sources.length) {
    const src = document.createElement("div");
    src.className = "chat-sources";
    src.innerHTML = "📎 " + sources.map(s => `<span>${s}</span>`).join("");
    wrap.appendChild(src);
  }

  msgBox.appendChild(wrap);
  scrollDown();
  return wrap;
}

async function sendMessage() {
  const question = input.value.trim();
  if (!question) return;

  input.value = "";
  sendBtn.disabled = true;
  appendMsg("user", question, null);

  const thinking = appendMsg("bot", "⏳ Consultando base de conhecimento…", null);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    if (res.status === 503) {
      thinking.querySelector(".bubble").textContent =
        "❌ Serviço LLM indisponível. Verifique se o Ollama está rodando.";
      return;
    }

    const data = await res.json();
    thinking.querySelector(".bubble").textContent = data.answer;

    if (data.sources && data.sources.length) {
      const src = document.createElement("div");
      src.className = "chat-sources";
      src.innerHTML = "📎 " + data.sources.map(s => `<span>${s}</span>`).join("");
      thinking.appendChild(src);
    }
    scrollDown();
  } catch (err) {
    thinking.querySelector(".bubble").textContent = "❌ Erro de comunicação com o servidor.";
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

async function resetChat() {
  await fetch("/chat/reset", { method: "POST" });
  msgBox.innerHTML = "";
  appendMsg("bot", "Histórico limpo. Faça sua nova pergunta.", null);
  input.focus();
}

// Enter to send, Shift+Enter for newline
input.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
