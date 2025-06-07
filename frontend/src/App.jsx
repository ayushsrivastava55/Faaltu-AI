import React, { useState, useEffect, useRef } from 'react'
import { Mic, Send, User, MessageCircle, Database, Activity, Sparkles } from 'lucide-react'
import axios from 'axios'
import './App.css'

// API Base URL
const API_BASE_URL = 'http://localhost:8080'

function App() {
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [systemHealth, setSystemHealth] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const messagesEndRef = useRef(null)

  // Initialize session on mount
  useEffect(() => {
    let storedSessionId = localStorage.getItem('conversation_session_id')
    if (!storedSessionId) {
      storedSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('conversation_session_id', storedSessionId)
    }
    setSessionId(storedSessionId)
    checkSystemHealth()
  }, [])

  const checkSystemHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`)
      setSystemHealth(response.data)
    } catch (error) {
      console.error('Health check failed:', error)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendTextMessage = async (e) => {
    e.preventDefault()
    if (!inputMessage.trim()) return

    const userMsg = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMsg])
    setInputMessage('')
    setIsLoading(true)

    try {
      const response = await axios.post(`${API_BASE_URL}/query`, {
        query: inputMessage,
        session_id: sessionId
      })

      const assistantMsg = {
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

      setMessages(prev => [...prev, assistantMsg])
    } catch (error) {
      const errorMsg = {
        id: Date.now() + 1,
        type: 'error',
        content: 'Error processing your request. Please try again.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  // Voice recording handlers
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
      window.currentRecorder = mediaRecorder

      setTimeout(() => {
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.stop()
          setIsRecording(false)
        }
      }, 10000)
    } catch (err) {
      alert('Microphone access denied or unavailable.')
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
    const voiceMsg = {
      id: Date.now(),
      type: 'user',
      content: '🎤 Voice message...',
      timestamp: new Date()
    }
    setMessages(prev => [...prev, voiceMsg])

    try {
      const formData = new FormData()
      formData.append('audio_file', audioBlob, 'recording.wav')
      formData.append('language', 'en')
      formData.append('session_id', sessionId)

      const response = await axios.post(`${API_BASE_URL}/voice-query`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      // Update message with transcribed query
      setMessages(prev => prev.map(msg => 
        msg.id === voiceMsg.id ? { ...msg, content: `🎤 "${response.data.query}"` } : msg
      ))

      const assistantMsg = {
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
      setMessages(prev => [...prev, assistantMsg])
    } catch {
      const errorMsg = {
        id: Date.now() + 1,
        type: 'error',
        content: 'Voice processing failed. Please try again.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <MessageCircle className="header-icon" size={32} />
          <h1>✨ Voice AI Assistant</h1>
        </div>
        <div className="header-right">
          <button onClick={() => {
            localStorage.removeItem('conversation_session_id')
            setMessages([])
            const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
            localStorage.setItem('conversation_session_id', newSessionId)
            setSessionId(newSessionId)
          }} className="new-conversation-button">
            <Sparkles size={18} />
            New Conversation
          </button>
        </div>
      </header>

      <main className="chat-container">
        <div className="messages">
          {messages.length === 0 && (
            <div className="message system">
              <div className="message-content">
                <p>👋 Welcome! Ask me anything about Voice AI or start a conversation.</p>
              </div>
            </div>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className={`message ${msg.type}`}>
              <div className="message-content">
                <p>{msg.content}</p>
                {msg.agents_consulted && msg.agents_consulted.length > 0 && (
                  <div className="agents-info">
                    <div className="agents-consulted">
                      <span className="agents-label">🤖 Agents consulted:</span>
                      <div className="agents-list">
                        {msg.agents_consulted.map((agent, idx) => (
                          <span key={idx} className="agent-badge">{agent.replace('_', ' ')}</span>
                        ))}
                      </div>
                    </div>
                    {msg.reasoning_approach && (
                      <div className="reasoning-approach">
                        <span className="reasoning-label">🧠 Approach:</span>
                        <span className="reasoning-text">{msg.reasoning_approach}</span>
                      </div>
                    )}
                    {msg.tools_used && msg.tools_used.length > 0 && (
                      <div className="tools-used">
                        <span className="tools-label">🔧 Tools used:</span>
                        <span className="tools-count">{msg.tools_used.length} tool(s)</span>
                      </div>
                    )}
                  </div>
                )}
                {msg.relationships && Object.keys(msg.relationships).length > 0 && (
                  <div className="relationships">
                    <Database className="relationship-icon" />
                    <span>Found {Object.values(msg.relationships).reduce((a, b) => a + b.count, 0)} related concepts</span>
                  </div>
                )}
                {msg.confidence && (
                  <div className="message-meta">
                    <span>💪 Confidence: {(msg.confidence * 100).toFixed(1)}%</span>
                    {msg.processing_time && (
                      <span>• ⚡ {(msg.processing_time * 1000).toFixed(0)}ms</span>
                    )}
                  </div>
                )}
              </div>
              <div className="message-time">{msg.timestamp.toLocaleTimeString()}</div>
            </div>
          ))}
          {isLoading && (
            <div className="message assistant loading">
              <div className="message-content">
                <div className="thinking">
                  <span></span><span></span><span></span>
                </div>
                <p>✨ Processing your request...</p>
                <div className="processing-info">
                  <span className="processing-label">🧠 Analyzing query and planning response</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={sendTextMessage} className="input-form">
          <input
            type="text"
            className="message-input"
            placeholder="✨ Ask me anything about Voice AI..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={isRecording ? stopVoiceRecording : startVoiceRecording}
            disabled={isLoading}
            className={`voice-button ${isRecording ? 'recording' : ''}`}
            title={isRecording ? "Stop recording" : "Start voice recording"}
          >
            <Mic size={28} />
          </button>
          <button
            type="submit"
            disabled={isLoading || !inputMessage.trim()}
            className="send-button"
            title="Send message"
          >
            <Send size={28} />
          </button>
        </form>
      </main>
    </div>
  )
}

export default App