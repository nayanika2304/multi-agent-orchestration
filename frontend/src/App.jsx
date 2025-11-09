import React, { useState, useRef, useEffect } from 'react'
import './App.css'

const API_BASE_URL = '/api/v1/agents'

// Utility function to clean and format response text
const formatResponse = (text) => {
  if (!text) return ''
  
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = text
  
  let cleaned = tempDiv.textContent || tempDiv.innerText || ''
  
  cleaned = cleaned
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
  
  cleaned = cleaned
    .split('\n')
    .map(line => line.trim())
    .join('\n')
  
  return cleaned.trim()
}

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([])
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('chat') // 'chat' or 'agents'
  const [agents, setAgents] = useState([])
  const [agentsLoading, setAgentsLoading] = useState(false)
  const [registerEndpoint, setRegisterEndpoint] = useState('')
  const [registerLoading, setRegisterLoading] = useState(false)
  const [unregisterLoading, setUnregisterLoading] = useState({})
  const messagesEndRef = useRef(null)
  const [sessionId] = useState(() => {
    return crypto.randomUUID ? crypto.randomUUID() : 
           `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  })

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (activeTab === 'agents') {
      loadAgents()
    }
  }, [activeTab])

  const loadAgents = async () => {
    setAgentsLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/list`)
      const data = await res.json()
      if (data.success) {
        setAgents(data.agents || [])
      } else {
        setError(data.error || 'Failed to load agents')
      }
    } catch (err) {
      setError(`Failed to load agents: ${err.message}`)
    } finally {
      setAgentsLoading(false)
    }
  }

  const handleRegisterAgent = async (e) => {
    e.preventDefault()
    if (!registerEndpoint.trim() || registerLoading) return

    setRegisterLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ endpoint: registerEndpoint.trim() }),
      })

      const data = await res.json()
      if (data.success) {
        setRegisterEndpoint('')
        await loadAgents()
      } else {
        setError(data.error || 'Failed to register agent')
      }
    } catch (err) {
      setError(`Failed to register agent: ${err.message}`)
    } finally {
      setRegisterLoading(false)
    }
  }

  const handleUnregisterAgent = async (agentIdentifier) => {
    if (unregisterLoading[agentIdentifier]) return

    setUnregisterLoading(prev => ({ ...prev, [agentIdentifier]: true }))
    setError(null)

    try {
      const res = await fetch(`${API_BASE_URL}/unregister`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ agent_identifier: agentIdentifier }),
      })

      const data = await res.json()
      if (data.success) {
        await loadAgents()
      } else {
        setError(data.error || 'Failed to unregister agent')
      }
    } catch (err) {
      setError(`Failed to unregister agent: ${err.message}`)
    } finally {
      setUnregisterLoading(prev => ({ ...prev, [agentIdentifier]: false }))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim() || loading) return

    const userMessage = query.trim()
    setQuery('')
    setError(null)
    setLoading(true)

    // Add user message
    const newUserMessage = {
      id: Date.now(),
      role: 'user',
      content: userMessage,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, newUserMessage])

    // Create assistant message placeholder
    const assistantMessageId = Date.now() + 1
    const newAssistantMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      metadata: null,
      isStreaming: true,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, newAssistantMessage])

    try {
      const response = await fetch(`${API_BASE_URL}/query/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          query: userMessage,
          session_id: sessionId
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'status') {
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMessageId 
                    ? { ...msg, content: data.message }
                    : msg
                ))
              } else if (data.type === 'metadata') {
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMessageId 
                    ? { ...msg, metadata: { agent: data.agent, confidence: data.confidence, reasoning: data.reasoning } }
                    : msg
                ))
              } else if (data.type === 'chunk') {
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMessageId 
                    ? { ...msg, content: msg.content + data.content }
                    : msg
                ))
              } else if (data.type === 'done') {
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMessageId 
                    ? { ...msg, isStreaming: false }
                    : msg
                ))
                setLoading(false)
              } else if (data.type === 'error') {
                setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId))
                setError(data.error)
                setLoading(false)
              }
            } catch (parseErr) {
              console.error('Error parsing SSE data:', parseErr, line)
            }
          }
        }
      }
    } catch (err) {
      setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId))
      setError(`Network error: ${err.message}`)
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <div className="chat-container">
        <header className="chat-header">
          <h1>Multi-Agent Orchestrator</h1>
          <p className="subtitle">Intelligent routing to specialized agents</p>
          <div className="tabs">
            <button
              className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              Chat
            </button>
            <button
              className={`tab ${activeTab === 'agents' ? 'active' : ''}`}
              onClick={() => setActiveTab('agents')}
            >
              Agents
            </button>
          </div>
        </header>

        {activeTab === 'chat' && (
          <>
            <div className="chat-messages">
              {messages.length === 0 && (
                <div className="welcome-message">
                  <p>Welcome! Ask me anything and I'll route your query to the best agent.</p>
                  <div className="example-buttons">
                    <button
                      onClick={() => setQuery("What time is it in New York?")}
                      className="example-button"
                      disabled={loading}
                    >
                      Time in New York
                    </button>
                    <button
                      onClick={() => setQuery("Solve x^2 - 4 = 0")}
                      className="example-button"
                      disabled={loading}
                    >
                      Solve Equation
                    </button>
                    <button
                      onClick={() => setQuery("Convert 100 USD to EUR")}
                      className="example-button"
                      disabled={loading}
                    >
                      Convert Currency
                    </button>
                    <button
                      onClick={() => setQuery("What is the weather in Tokyo?")}
                      className="example-button"
                      disabled={loading}
                    >
                      Weather Query
                    </button>
                  </div>
                </div>
              )}
              
              {messages.map((message) => (
                <div key={message.id} className={`message ${message.role}`}>
                  <div className="message-content">
                    {message.role === 'user' ? (
                      <div className="message-bubble user-bubble">
                        <p>{message.content}</p>
                      </div>
                    ) : (
                      <div className="message-bubble assistant-bubble">
                        {message.metadata && (
                          <div className="message-metadata">
                            {message.metadata.agent && (
                              <span className="metadata-badge">
                                {message.metadata.agent}
                                {message.metadata.confidence !== null && (
                                  <span className="confidence">{(message.metadata.confidence * 100).toFixed(0)}%</span>
                                )}
                              </span>
                            )}
                          </div>
                        )}
                        <div className="message-text">
                          {message.content ? (
                            <p>{formatResponse(message.content)}</p>
                          ) : (
                            <p className="placeholder">Processing...</p>
                          )}
                          {message.isStreaming && (
                            <span className="streaming-indicator"></span>
                          )}
                        </div>
                        {message.metadata?.reasoning && (
                          <details className="reasoning">
                            <summary>Reasoning</summary>
                            <p>{formatResponse(message.metadata.reasoning)}</p>
                          </details>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {error && (
                <div className="message error">
                  <div className="message-bubble error-bubble">
                    <p>{error}</p>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSubmit} className="chat-input-form">
              <div className="input-wrapper">
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Type your message here..."
                  className="chat-input"
                  rows="1"
                  disabled={loading}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSubmit(e)
                    }
                  }}
                />
                <button
                  type="submit"
                  className="send-button"
                  disabled={loading || !query.trim()}
                >
                  {loading ? (
                    <span className="button-spinner"></span>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="22" y1="2" x2="11" y2="13"></line>
                      <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                  )}
                </button>
              </div>
            </form>
          </>
        )}

        {activeTab === 'agents' && (
          <div className="agents-panel">
            <div className="agents-header">
              <h2>Agent Management</h2>
              <button onClick={loadAgents} className="refresh-button" disabled={agentsLoading}>
                {agentsLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>

            {error && (
              <div className="error-message">
                <p>{error}</p>
              </div>
            )}

            <div className="register-section">
              <h3>Register New Agent</h3>
              <form onSubmit={handleRegisterAgent} className="register-form">
                <input
                  type="text"
                  value={registerEndpoint}
                  onChange={(e) => setRegisterEndpoint(e.target.value)}
                  placeholder="Agent endpoint (e.g., http://localhost:8001)"
                  className="endpoint-input"
                  disabled={registerLoading}
                />
                <button
                  type="submit"
                  className="register-button"
                  disabled={registerLoading || !registerEndpoint.trim()}
                >
                  {registerLoading ? 'Registering...' : 'Register'}
                </button>
              </form>
            </div>

            <div className="agents-list">
              <h3>Registered Agents ({agents.length})</h3>
              {agentsLoading ? (
                <div className="loading-state">Loading agents...</div>
              ) : agents.length === 0 ? (
                <div className="empty-state">No agents registered</div>
              ) : (
                <div className="agents-grid">
                  {agents.map((agent) => (
                    <div key={agent.agent_id} className="agent-card">
                      <div className="agent-header">
                        <h4>{agent.name}</h4>
                        <button
                          onClick={() => handleUnregisterAgent(agent.agent_id)}
                          className="unregister-button"
                          disabled={unregisterLoading[agent.agent_id]}
                        >
                          {unregisterLoading[agent.agent_id] ? 'Removing...' : 'Remove'}
                        </button>
                      </div>
                      <p className="agent-description">{agent.description}</p>
                      <div className="agent-details">
                        <div className="agent-detail-item">
                          <span className="detail-label">Endpoint:</span>
                          <span className="detail-value">{agent.endpoint}</span>
                        </div>
                        <div className="agent-detail-item">
                          <span className="detail-label">ID:</span>
                          <span className="detail-value">{agent.agent_id}</span>
                        </div>
                        {agent.skills && agent.skills.length > 0 && (
                          <div className="agent-skills">
                            <span className="detail-label">Skills:</span>
                            <div className="skills-list">
                              {agent.skills.slice(0, 3).map((skill, idx) => (
                                <span key={idx} className="skill-tag">
                                  {skill.name || skill}
                                </span>
                              ))}
                              {agent.skills.length > 3 && (
                                <span className="skill-tag">+{agent.skills.length - 3} more</span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
