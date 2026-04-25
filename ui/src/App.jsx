import { useState } from 'react'

export default function App() {
  const [input, setInput] = useState('')
  const [output, setOutput] = useState('')
  const [next, setNext] = useState('')
  const [state, setState] = useState(null)

  const analizEt = async () => {
    const res = await fetch('http://localhost:5001/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: input, state })
    })
    const data = await res.json()
    setOutput(data.message)
    setNext(data.next)
    setState(data.state)
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
          <div>{output}</div>
          <div style={{ opacity: 0.6 }}>{next}</div>
        </div>
      </div>
    </div>
  )
}
