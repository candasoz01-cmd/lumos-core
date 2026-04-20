import { useState } from "react"

export default function App() {
  const [input, setInput] = useState("")
  const [message, setMessage] = useState("")
  const [next, setNext] = useState("")

  async function analizEt() {
    setMessage("Analiz ediliyor...")
    setNext("")

    try {
      const res = await fetch("http://127.0.0.1:5001/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ text: input })
      })

      const data = await res.json()

      setMessage(data.message || "boş")
      setNext(data.next || "")
    } catch (e) {
      setMessage("Hata: backend yok")
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0b1020',
      color: '#e5e7eb',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <div style={{ width: '100%', maxWidth: '900px' }}>

        <h1>Sorunu yaz</h1>

        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          style={{ width: '100%', padding: '15px', marginBottom: '10px' }}
        />

        <button onClick={analizEt}>Analiz Et</button>

        <div style={{ marginTop: '20px' }}>
          <div>{message}</div>
          <div style={{ opacity: 0.6 }}>{next}</div>
        </div>

      </div>
    </div>
  )
}
