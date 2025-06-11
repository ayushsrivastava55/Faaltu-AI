"use client";

import { useState, useRef, useEffect } from 'react';
import { FaPaperPlane, FaRobot, FaUser, FaSpinner } from 'react-icons/fa';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

interface ChatProps {
  initialMessages?: Message[];
  onSendMessage: (message: string) => Promise<void>;
  isProcessing: boolean;
  assistantResponse?: string;
}

const Chat = ({ initialMessages = [], onSendMessage, isProcessing, assistantResponse }: ChatProps) => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Add assistant response when it changes
  useEffect(() => {
    if (assistantResponse && !isProcessing) {
      const lastMessage = messages[messages.length - 1];
      // Only add if it's not already the last message
      if (!lastMessage || lastMessage.sender !== 'assistant' || lastMessage.text !== assistantResponse) {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          text: assistantResponse,
          sender: 'assistant',
          timestamp: new Date()
        }]);
      }
    }
  }, [assistantResponse, isProcessing]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;
    
    // Add user message to chat
    const newMessage: Message = {
      id: Date.now().toString(),
      text: input,
      sender: 'user',
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, newMessage]);
    setInput('');
    
    // Send to parent component
    await onSendMessage(input);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="flex flex-col h-[600px] bg-gradient-to-br from-gray-900 to-gray-800 rounded-lg shadow-lg border border-gray-700">
      {/* Chat header */}
      <div className="bg-gradient-to-r from-purple-900 to-indigo-900 text-white p-4 rounded-t-lg">
        <h2 className="text-xl font-semibold flex items-center">
          <FaRobot className="mr-2 text-purple-300" /> FinMate Assistant
        </h2>
        <p className="text-sm opacity-80">Ask me anything about finance</p>
      </div>
      
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-900">
        {messages.length === 0 ? (
          <div className="text-center text-gray-400 my-8">
            <p>No messages yet. Start a conversation!</p>
          </div>
        ) : (
          messages.map(message => (
            <div 
              key={message.id} 
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div 
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  message.sender === 'user' 
                    ? 'bg-indigo-800 text-gray-100 rounded-tr-none border border-indigo-700' 
                    : 'bg-gray-800 text-gray-100 rounded-tl-none border border-gray-700'
                }`}
              >
                <div className="flex items-center mb-1">
                  {message.sender === 'assistant' ? (
                    <FaRobot className="mr-2 text-purple-400" />
                  ) : (
                    <FaUser className="mr-2 text-indigo-400" />
                  )}
                  <span className="text-xs text-gray-400">{formatTime(message.timestamp)}</span>
                </div>
                <p className="whitespace-pre-wrap">{message.text}</p>
              </div>
            </div>
          ))
        )}
        
        {isProcessing && (
          <div className="flex justify-start">
            <div className="bg-gray-800 text-gray-100 rounded-2xl rounded-tl-none px-4 py-3 max-w-[80%] border border-gray-700">
              <div className="flex items-center">
                <FaRobot className="mr-2 text-purple-400" />
                <FaSpinner className="animate-spin text-purple-400" />
              </div>
              <p className="text-sm text-gray-400 mt-1">Thinking...</p>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input area */}
      <div className="border-t border-gray-700 p-4 bg-gray-800 rounded-b-lg">
        <form onSubmit={handleSubmit} className="flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 bg-gray-700 border border-gray-600 text-gray-100 rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500 placeholder-gray-400"
            disabled={isProcessing}
          />
          <button
            type="submit"
            className={`ml-2 rounded-full p-2 ${
              isProcessing || !input.trim() 
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                : 'bg-purple-700 text-white hover:bg-purple-600'
            }`}
            disabled={isProcessing || !input.trim()}
          >
            <FaPaperPlane />
          </button>
        </form>
      </div>
    </div>
  );
};

export default Chat;
