import { useState } from "react"

export default function App() {
  const [input, setInput] = useState("")
  const [output, setOutput] = useState("")

  function analizEt() {
    const girdi = input.toLowerCase()

    if (girdi.includes("açılmıyor")) {
      setOutput("→ Güç hattını kontrol et\n→ Sigorta sonrası hat\n→ SMPS primer katı kontrol et")
    } 
    else if (girdi.includes("sigorta")) {
      setOutput("→ Kısa devre ihtimali\n→ Diyot / MOSFET kontrol et\n→ Köprü diyot bak")
    } 
    else {
      setOutput("→ Daha fazla bilgi ver, daraltalım")
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0b1020',
      color: '#e5e7eb',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'Arial, sans-serif'
    }}>
      <div style={{ width: '100%', maxWidth: '900px', padding: '40px' }}>

        <div style={{ fontSize: '12px', letterSpacing: '3px', opacity: 0.6 }}>
          LUMOS
        </div>

        <h1 style={{ fontSize: '48px', marginBottom: '20px' }}>
          Sorunu yaz. Gereksizi keselim.
        </h1>

        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Örn: cihaz açılmıyor..."
          style={{
            width: '100%',
            padding: '16px',
            borderRadius: '10px',
            border: 'none',
            fontSize: '16px',
            marginBottom: '20px'
          }}
        />

        <button onClick={analizEt} style={{
          background: '#e5e7eb',
          color: '#0b1020',
          border: 'none',
          padding: '14px 20px',
          borderRadius: '10px',
          fontSize: '16px',
          cursor: 'pointer'
        }}>
          Analiz Et
        </button>

        {output && (
          <div style={{
            marginTop: '30px',
            background: '#111827',
            padding: '20px',
            borderRadius: '10px',
            whiteSpace: 'pre-line'
          }}>
            {output}
          </div>
        )}

      </div>
    </div>
  )
}
