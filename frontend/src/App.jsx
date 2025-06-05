import { useState, useEffect } from 'react'
import { Mic, Send, User, LogOut, MessageCircle, Database, Activity } from 'lucide-react'
import axios from 'axios'
import './App.css'

// API Configuration
const API_BASE_URL = 'http://localhost:8080'

function App() {
  const [user, setUser] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [systemHealth, setSystemHealth] = useState(null)
  const [authForm, setAuthForm] = useState({ username: '', password: '' })
  const [showAuth, setShowAuth] = useState(true)
  const [sessionId, setSessionId] = useState(null)

  // Initialize session on component mount
  useEffect(() => {
    // Get existing session from localStorage or create new one
    let storedSessionId = localStorage.getItem('conversation_session_id')
    if (!storedSessionId) {
      storedSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('conversation_session_id', storedSessionId)
    }
    setSessionId(storedSessionId)
    checkSystemHealth()
  }, [])

  // Function to reset session (for new conversations)
  const resetSession = () => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem('conversation_session_id', newSessionId)
    setSessionId(newSessionId)
    setMessages([])
  }

  const checkSystemHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`)
      setSystemHealth(response.data)
    } catch (error) {
      console.error('Health check failed:', error)
    }
  }

  const login = async (e) => {
    e.preventDefault()
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, authForm)
      const { access_token, user_info } = response.data
      
      localStorage.setItem('token', access_token)
      setUser(user_info)
      setShowAuth(false)
      
      // Add welcome message
      setMessages([{
        id: Date.now(),
        type: 'system',
        content: `Welcome back, ${user_info.full_name}! Your Voice AI Assistant is ready.`,
        timestamp: new Date()
      }])
    } catch (error) {
      alert('Login failed. Try username: demo, password: demo123')
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
    setShowAuth(true)
    setMessages([])
  }

  const sendTextMessage = async (e) => {
    e.preventDefault()
    if (!inputMessage.trim()) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      const token = localStorage.getItem('token')
      const response = await axios.post(
        `${API_BASE_URL}/query`,
        {
          query: inputMessage,
          session_id: sessionId
        },
        token ? { headers: { Authorization: `Bearer ${token}` } } : {}
      )

      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: response.data.response,
        confidence: response.data.confidence,
        relationships: response.data.relationships,
        processing_time: response.data.processing_time,
        agents_consulted: response.data.agents_consulted || [],
        tools_used: response.data.tools_used || [],
        reasoning_approach: response.data.reasoning_approach,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      const audioChunks = []

      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data)
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' })
        await sendVoiceMessage(audioBlob)
        stream.getTracks().forEach(track => track.stop())
      }

      setIsRecording(true)
      mediaRecorder.start()

      // Stop recording after 10 seconds max
      setTimeout(() => {
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.stop()
          setIsRecording(false)
        }
      }, 10000)

      // Store recorder for manual stop
      window.currentRecorder = mediaRecorder
    } catch (error) {
      alert('Microphone access denied or not available')
    }
  }

  const stopVoiceRecording = () => {
    if (window.currentRecorder && window.currentRecorder.state === 'recording') {
      window.currentRecorder.stop()
      setIsRecording(false)
    }
  }

  const sendVoiceMessage = async (audioBlob) => {
    setIsLoading(true)
    
    const voiceMessage = {
      id: Date.now(),
      type: 'user',
      content: '🎤 Voice message...',
      timestamp: new Date()
    }
    setMessages(prev => [...prev, voiceMessage])

    try {
      const formData = new FormData()
      formData.append('audio_file', audioBlob, 'recording.wav')
      formData.append('language', 'en')
      formData.append('session_id', sessionId)

      const token = localStorage.getItem('token')
      const response = await axios.post(
        `${API_BASE_URL}/voice-query`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            ...(token ? { Authorization: `Bearer ${token}` } : {})
          }
        }
      )

      // Update the voice message with transcription
      setMessages(prev => prev.map(msg => 
        msg.id === voiceMessage.id 
          ? { ...msg, content: `🎤 "${response.data.query}"` }
          : msg
      ))

      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: response.data.response,
        confidence: response.data.confidence,
        relationships: response.data.relationships,
        processing_time: response.data.processing_time,
        agents_consulted: response.data.agents_consulted || [],
        tools_used: response.data.tools_used || [],
        reasoning_approach: response.data.reasoning_approach,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: 'Voice processing failed. Please try again.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  if (showAuth) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <MessageCircle className="auth-icon" />
            <h1>Voice AI Assistant</h1>
            <p>Realistic Production Demo</p>
          </div>
          
          <form onSubmit={login} className="auth-form">
            <input
              type="text"
              placeholder="Username (try: demo)"
              value={authForm.username}
              onChange={(e) => setAuthForm(prev => ({ ...prev, username: e.target.value }))}
              required
            />
            <input
              type="password"
              placeholder="Password (try: demo123)"
              value={authForm.password}
              onChange={(e) => setAuthForm(prev => ({ ...prev, password: e.target.value }))}
              required
            />
            <button type="submit" className="auth-button">
              Sign In
            </button>
          </form>

          <div className="system-status">
            <h3><Activity className="status-icon" /> System Status</h3>
            {systemHealth ? (
              <div className="status-grid">
                <div className={`status-item ${systemHealth.services.api === 'healthy' ? 'healthy' : 'degraded'}`}>
                  API: {systemHealth.services.api}
                </div>
                <div className={`status-item ${systemHealth.services.voice_processor === 'healthy' ? 'healthy' : 'degraded'}`}>
                  Voice: {systemHealth.services.voice_processor}
                </div>
                <div className={`status-item ${systemHealth.services.graph_intelligence === 'neo4j' ? 'healthy' : 'degraded'}`}>
                  Graph: {systemHealth.services.graph_intelligence}
                </div>
                <div className={`status-item ${systemHealth.services.knowledge_base === 'healthy' ? 'healthy' : 'degraded'}`}>
                  Knowledge: {systemHealth.services.knowledge_base}
                </div>
              </div>
            ) : (
              <p>Checking system status...</p>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <MessageCircle className="header-icon" />
          <h1>Voice AI Assistant</h1>
          {sessionId && (
            <span className="session-info">Session: {sessionId.split('_')[1]}</span>
          )}
        </div>
        <div className="header-right">
          <button onClick={resetSession} className="new-conversation-button">
            🔄 New Conversation
          </button>
          <div className="user-info">
            <User className="user-icon" />
            <span>{user?.full_name}</span>
          </div>
          <button onClick={logout} className="logout-button">
            <LogOut />
          </button>
        </div>
      </header>

      <main className="chat-container">
        <div className="messages">
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.type}`}>
              <div className="message-content">
                <p>{message.content}</p>
                {message.agents_consulted && message.agents_consulted.length > 0 && (
                  <div className="agents-info">
                    <div className="agents-consulted">
                      <span className="agents-label">🤖 Agents consulted:</span>
                      <div className="agents-list">
                        {message.agents_consulted.map((agent, index) => (
                          <span key={index} className="agent-badge">
                            {agent.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                    </div>
                    {message.reasoning_approach && (
                      <div className="reasoning-approach">
                        <span className="reasoning-label">🧠 Approach:</span>
                        <span className="reasoning-text">{message.reasoning_approach}</span>
                      </div>
                    )}
                    {message.tools_used && message.tools_used.length > 0 && (
                      <div className="tools-used">
                        <span className="tools-label">🔧 Tools used:</span>
                        <span className="tools-count">{message.tools_used.length} tool(s)</span>
                      </div>
                    )}
                  </div>
                )}
                {message.relationships && Object.keys(message.relationships).length > 0 && (
                  <div className="relationships">
                    <Database className="relationship-icon" />
                    <span>Found {Object.values(message.relationships).reduce((total, rel) => total + rel.count, 0)} related concepts</span>
                  </div>
                )}
                {message.confidence && (
                  <div className="message-meta">
                    <span>Confidence: {(message.confidence * 100).toFixed(1)}%</span>
                    {message.processing_time && (
                      <span>• {(message.processing_time * 1000).toFixed(0)}ms</span>
                    )}
                  </div>
                )}
              </div>
              <div className="message-time">
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message assistant loading">
              <div className="message-content">
                <div className="thinking">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <p>Processing your request...</p>
                <div className="processing-info">
                  <span className="processing-label">🧠 Analyzing query and planning response</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <form onSubmit={sendTextMessage} className="input-form">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Ask me anything about Voice AI..."
            disabled={isLoading}
            className="message-input"
          />
          <button
            type="button"
            onClick={isRecording ? stopVoiceRecording : startVoiceRecording}
            disabled={isLoading}
            className={`voice-button ${isRecording ? 'recording' : ''}`}
          >
            <Mic />
          </button>
          <button
            type="submit"
            disabled={isLoading || !inputMessage.trim()}
            className="send-button"
          >
            <Send />
          </button>
        </form>
      </main>
    </div>
  )
}

export default App
