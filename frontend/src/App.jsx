import React, { useState, useEffect, useRef } from 'react'
import { 
  Mic, Send, User, MessageCircle, Database, Activity, Sparkles,
  Upload, FileText, Music, Globe, Shield, CheckCircle, AlertCircle
} from 'lucide-react'
import axios from 'axios'
import './App.css'
import './AdminPanel.css'  // New CSS file for admin styles

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
  const [showAdminPanel, setShowAdminPanel] = useState(false)
  const [adminAuth, setAdminAuth] = useState({ username: '', password: '', isAuthenticated: false })
  const [uploadStatus, setUploadStatus] = useState({ status: 'idle', message: '', type: 'info' })
  const [uploadStats, setUploadStats] = useState(null)


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

const handleAdminLogin = async (e) => {
    e.preventDefault()
    
    try {
      // Test authentication by fetching upload status
      const response = await axios.get(`${API_BASE_URL}/admin/uploads/status`, {
        auth: {
          username: adminAuth.username,
          password: adminAuth.password
        }
      })
      
      setAdminAuth(prev => ({ ...prev, isAuthenticated: true }))
      setUploadStats(response.data)
      setUploadStatus({ status: 'success', message: 'Admin authentication successful!', type: 'success' })
      
    } catch (error) {
      setUploadStatus({ 
        status: 'error', 
        message: 'Invalid admin credentials', 
        type: 'error' 
      })
    }
  }

  const handleAdminLogout = () => {
    setAdminAuth({ username: '', password: '', isAuthenticated: false })
    setUploadStats(null)
    setUploadStatus({ status: 'idle', message: '', type: 'info' })
  }

  // File upload handlers
  const handleFileUpload = async (file, uploadType) => {
    setUploadStatus({ status: 'loading', message: 'Uploading file...', type: 'info' })
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const endpoint = uploadType === 'audio' ? 'audio' : 
                     uploadType === 'faq' ? 'faq' : 'json'
      
      const response = await axios.post(`${API_BASE_URL}/admin/upload/${endpoint}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        auth: {
          username: adminAuth.username,
          password: adminAuth.password
        }
      })
      
      setUploadStatus({ 
        status: 'success', 
        message: response.data.message, 
        type: 'success' 
      })
      
      // Refresh upload stats
      await fetchUploadStats()
      
    } catch (error) {
      setUploadStatus({ 
        status: 'error', 
        message: error.response?.data?.detail || 'Upload failed', 
        type: 'error' 
      })
    }
  }

  const handleUrlUpload = async (url, category = 'general') => {
    setUploadStatus({ status: 'loading', message: 'Scraping website...', type: 'info' })
    
    try {
      const response = await axios.post(`${API_BASE_URL}/admin/upload/url`, {
        url: url,
        category: category
      }, {
        auth: {
          username: adminAuth.username,
          password: adminAuth.password
        }
      })
      
      setUploadStatus({ 
        status: 'success', 
        message: response.data.message, 
        type: 'success' 
      })
      
      // Refresh upload stats
      await fetchUploadStats()
      
    } catch (error) {
      setUploadStatus({ 
        status: 'error', 
        message: error.response?.data?.detail || 'URL upload failed', 
        type: 'error' 
      })
    }
  }

  const fetchUploadStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/uploads/status`, {
        auth: {
          username: adminAuth.username,
          password: adminAuth.password
        }
      })
      setUploadStats(response.data)
    } catch (error) {
      console.error('Failed to fetch upload stats:', error)
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
          <button 
            onClick={() => setShowAdminPanel(!showAdminPanel)}
            className={`admin-toggle-button ${showAdminPanel ? 'active' : ''}`}
          >
            <Shield size={18} />
            Admin Panel
          </button>
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

      <div className="main-content">
        {/* Admin Panel */}
        {showAdminPanel && (
          <div className="admin-panel">
            <div className="admin-panel-header">
              <h2>Admin Data Upload Panel</h2>
              {adminAuth.isAuthenticated && (
                <button onClick={handleAdminLogout} className="logout-button">
                  Logout
                </button>
              )}
            </div>

            {!adminAuth.isAuthenticated ? (
              <AdminLoginForm 
                adminAuth={adminAuth}
                setAdminAuth={setAdminAuth}
                onLogin={handleAdminLogin}
                uploadStatus={uploadStatus}
              />
            ) : (
              <AdminUploadPanel 
                onFileUpload={handleFileUpload}
                onUrlUpload={handleUrlUpload}
                uploadStatus={uploadStatus}
                uploadStats={uploadStats}
              />
            )}
          </div>
        )}

        {/* Main Chat Interface */}
        <main className={`chat-container ${showAdminPanel ? 'with-admin-panel' : ''}`}>
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
    </div>
  )
}

// Admin Login Form Component
function AdminLoginForm({ adminAuth, setAdminAuth, onLogin, uploadStatus }) {
  return (
    <form onSubmit={onLogin} className="admin-login-form">
      <div className="form-group">
        <label>Username:</label>
        <input
          type="text"
          value={adminAuth.username}
          onChange={(e) => setAdminAuth(prev => ({ ...prev, username: e.target.value }))}
          placeholder="admin"
          required
        />
      </div>
      <div className="form-group">
        <label>Password:</label>
        <input
          type="password"
          value={adminAuth.password}
          onChange={(e) => setAdminAuth(prev => ({ ...prev, password: e.target.value }))}
          placeholder="Enter admin password"
          required
        />
      </div>
      <button type="submit" className="login-button">
        <Shield size={16} />
        Authenticate
      </button>
      
      <StatusMessage status={uploadStatus} />
    </form>
  )
}

// Admin Upload Panel Component
function AdminUploadPanel({ onFileUpload, onUrlUpload, uploadStatus, uploadStats }) {
  const [activeTab, setActiveTab] = useState('files')
  const [urlInput, setUrlInput] = useState('')
  const [categoryInput, setCategoryInput] = useState('general')

  return (
    <div className="admin-upload-panel">
      <div className="upload-tabs">
        <button 
          className={`tab-button ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => setActiveTab('files')}
        >
          <Upload size={16} />
          File Upload
        </button>
        <button 
          className={`tab-button ${activeTab === 'url' ? 'active' : ''}`}
          onClick={() => setActiveTab('url')}
        >
          <Globe size={16} />
          Website URL
        </button>
        <button 
          className={`tab-button ${activeTab === 'stats' ? 'active' : ''}`}
          onClick={() => setActiveTab('stats')}
        >
          <Database size={16} />
          Statistics
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'files' && (
          <FileUploadTab onFileUpload={onFileUpload} />
        )}
        
        {activeTab === 'url' && (
          <UrlUploadTab 
            urlInput={urlInput}
            setUrlInput={setUrlInput}
            categoryInput={categoryInput}
            setCategoryInput={setCategoryInput}
            onUrlUpload={onUrlUpload}
          />
        )}
        
        {activeTab === 'stats' && (
          <StatsTab uploadStats={uploadStats} />
        )}
      </div>

      <StatusMessage status={uploadStatus} />
    </div>
  )
}

// File Upload Tab Component
function FileUploadTab({ onFileUpload }) {
  const handleFileChange = (e, type) => {
    const file = e.target.files[0]
    if (file) {
      onFileUpload(file, type)
    }
  }

  return (
    <div className="file-upload-tab">
      <div className="upload-section">
        <h3><FileText size={20} /> JSON Files</h3>
        <p>Upload JSON data files for knowledge base</p>
        <input
          type="file"
          accept=".json"
          onChange={(e) => handleFileChange(e, 'json')}
          className="file-input"
        />
      </div>

      <div className="upload-section">
        <h3><FileText size={20} /> FAQ Files</h3>
        <p>Upload FAQ content in JSON, TXT, or MD format</p>
        <input
          type="file"
          accept=".json,.txt,.md"
          onChange={(e) => handleFileChange(e, 'faq')}
          className="file-input"
        />
      </div>

      <div className="upload-section">
        <h3><Music size={20} /> Audio Files</h3>
        <p>Upload voice recordings for training</p>
        <input
          type="file"
          accept=".mp3,.wav,.m4a,.ogg"
          onChange={(e) => handleFileChange(e, 'audio')}
          className="file-input"
        />
      </div>
    </div>
  )
}

// URL Upload Tab Component
function UrlUploadTab({ urlInput, setUrlInput, categoryInput, setCategoryInput, onUrlUpload }) {
  const handleUrlSubmit = (e) => {
    e.preventDefault()
    if (urlInput.trim()) {
      onUrlUpload(urlInput.trim(), categoryInput)
      setUrlInput('')
    }
  }

  return (
    <div className="url-upload-tab">
      <form onSubmit={handleUrlSubmit} className="url-form">
        <div className="form-group">
          <label>Website URL:</label>
          <input
            type="url"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://example.com"
            required
            className="url-input"
          />
        </div>
        
        <div className="form-group">
          <label>Category:</label>
          <select
            value={categoryInput}
            onChange={(e) => setCategoryInput(e.target.value)}
            className="category-select"
          >
            <option value="general">General</option>
            <option value="faq">FAQ</option>
            <option value="documentation">Documentation</option>
            <option value="news">News</option>
            <option value="tutorial">Tutorial</option>
          </select>
        </div>

        <button type="submit" className="url-submit-button">
          <Globe size={16} />
          Scrape & Upload
        </button>
      </form>
    </div>
  )
}

// Statistics Tab Component
function StatsTab({ uploadStats }) {
  if (!uploadStats) {
    return <div className="stats-loading">Loading statistics...</div>
  }

  return (
    <div className="stats-tab">
      <div className="stats-overview">
        <h3>Upload Statistics</h3>
        <div className="stats-cards">
          <div className="stat-card">
            <h4>Total Sources</h4>
            <p className="stat-number">{uploadStats.total_sources}</p>
          </div>
          
          {Object.entries(uploadStats.by_type || {}).map(([type, count]) => (
            <div key={type} className="stat-card">
              <h4>{type.charAt(0).toUpperCase() + type.slice(1)}</h4>
              <p className="stat-number">{count}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="recent-uploads">
        <h3>Recent Uploads</h3>
        <div className="uploads-list">
          {uploadStats.recent_uploads?.map((upload, index) => (
            <div key={index} className="upload-item">
              <span className="upload-type">{upload.type}</span>
              <span className="upload-filename">{upload.filename}</span>
              <span className="upload-date">
                {new Date(upload.uploaded_at).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Status Message Component
function StatusMessage({ status }) {
  if (status.status === 'idle') return null

  const getIcon = () => {
    switch (status.type) {
      case 'success': return <CheckCircle size={16} />
      case 'error': return <AlertCircle size={16} />
      default: return <Activity size={16} />
    }
  }

  return (
    <div className={`status-message ${status.type}`}>
      {getIcon()}
      <span>{status.message}</span>
    </div>
  )
}

export default App