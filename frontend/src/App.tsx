import { useEffect, useState } from 'react'
import { Md2WordApp } from './apps/md2word/Md2WordApp'

type Tool = {
  id: string
  label: string
  icon: string
  description: string
}

export function App() {
  const [tools, setTools] = useState<Tool[]>([])
  const [activeToolId, setActiveToolId] = useState('md2word')
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    fetch('/api/tools')
      .then((response) => response.json())
      .then((data: Tool[]) => setTools(data))
      .catch(() => {
        setTools([
          {
            id: 'md2word',
            label: 'MD2Word',
            icon: '/icons/md2word.svg',
            description: 'Markdown 转 Word 工具',
          },
        ])
      })
  }, [])

  return (
    <div className="workspace-shell">
      <aside className={collapsed ? 'tool-rail collapsed' : 'tool-rail'}>
        <button className="rail-toggle" onClick={() => setCollapsed((value) => !value)}>
          {collapsed ? '›' : '‹'}
        </button>
        <div className="tool-list">
          {tools.map((tool) => (
            <button
              key={tool.id}
              className={tool.id === activeToolId ? 'tool-button active' : 'tool-button'}
              onClick={() => setActiveToolId(tool.id)}
              title={tool.label}
            >
              <img src={tool.icon} alt={tool.label} />
              <span className="tool-label">{tool.label}</span>
            </button>
          ))}
        </div>
      </aside>
      <main className="tool-canvas">
        {activeToolId === 'md2word' ? <Md2WordApp /> : null}
      </main>
    </div>
  )
}
